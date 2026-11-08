from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from cleaning import (
    CLEANING_VERSION, EXPECTED_COLUMNS, KNOWLEDGE_COLUMNS, PAIRS,
    PRESENTER_COLUMNS, clean_survey, load_survey, summarize_quality,
    _text as normalize_source_text,
)

PIPELINE_VERSION = "1.0.0"
DEFAULT_MIN_GROUP_N = 20
LIMITATIONS = [
    "Knowledge responses are retrospective self-reports, not a causal pretest.",
    "Likert scores are ordinal; means summarize coded 1-5 responses.",
    "Survey rows and distinct IDs do not establish unique individuals.",
    "County identifies training affiliation, not participant residence.",
    "Multi-role rows count once per selected role; role groups overlap.",
    "Response share does not measure population representation or need.",
    "Willingness results cover valid answers only; missing answers are not zero.",
    "Small-group warnings are statistical cautions, not privacy guarantees.",
]


@dataclass
class PipelineResult:
    """Private in-memory data plus aggregate results for other team modules."""

    raw_df: pd.DataFrame
    clean_df: pd.DataFrame
    audit: dict
    quality: dict
    summary: dict


def _rate(count, denominator):
    return float(count / denominator) if denominator else None


def _check_min_n(min_group_n):
    if isinstance(min_group_n, bool) or not isinstance(min_group_n, int) or min_group_n < 1:
        raise ValueError("min_group_n must be a positive integer.")


def _paired_stats(before, after, total_rows):
    paired = pd.DataFrame({"before": before, "after": after}).dropna()
    n = len(paired)
    change = paired["after"] - paired["before"]
    up = int((change > 0).sum())
    same = int((change == 0).sum())
    down = int((change < 0).sum())
    return {
        "n": n,
        "denominator_rows": total_rows,
        "missing_pair_rows": total_rows - n,
        "before_mean": float(paired["before"].mean()) if n else None,
        "after_mean": float(paired["after"].mean()) if n else None,
        "mean_change": float(change.mean()) if n else None,
        "count_up": up, "count_same": same, "count_down": down,
        "share_up": _rate(up, n),
        "share_same": _rate(same, n),
        "share_down": _rate(down, n),
    }


def summarize_knowledge(clean_df: pd.DataFrame) -> dict:
    """Use a separate matched sample for each topic; all six for overall.

    The overall score is each row's equal-weight mean across three topics.
    It is descriptive, not a validated composite measure.
    """
    topics = {
        topic: _paired_stats(clean_df[before], clean_df[after], len(clean_df))
        for topic, (before, after) in PAIRS.items()
    }
    complete = clean_df.dropna(subset=KNOWLEDGE_COLUMNS)
    before_cols = [pair[0] for pair in PAIRS.values()]
    after_cols = [pair[1] for pair in PAIRS.values()]
    overall = _paired_stats(
        complete[before_cols].mean(axis=1),
        complete[after_cols].mean(axis=1), len(clean_df),
    )
    return {"topics": topics, "overall_three_topic_mean": overall}


def _distribution(series, total_rows, expected_values=()):
    valid = series.dropna()
    counts = valid.value_counts().to_dict()
    # Include any valid fractional 0-10 ratings rather than silently losing them.
    values = sorted(set(expected_values) | set(counts))
    return {
        "valid_n": len(valid),
        "denominator_rows": total_rows,
        "missing_or_invalid_n": total_rows - len(valid),
        "values": [
            {"value": float(value), "count": int(counts.get(value, 0)),
             "share": _rate(counts.get(value, 0), len(valid))}
            for value in values
        ],
    }


def summarize_distributions(clean_df: pd.DataFrame) -> dict:
    """Knowledge before/after distributions use the same paired rows per topic."""
    n = len(clean_df)
    knowledge = {}
    for topic, (before, after) in PAIRS.items():
        paired = clean_df[[before, after]].dropna()
        knowledge[topic] = {
            "before": _distribution(paired[before], n, range(1, 6)),
            "after": _distribution(paired[after], n, range(1, 6)),
        }
    return {
        "knowledge_paired": knowledge,
        "training_experience": {
            c: _distribution(clean_df[c], n, range(1, 6)) for c in PRESENTER_COLUMNS
        },
        "recommend_training": _distribution(clean_df["recommend_training"], n, range(11)),
        "willingness_to_call": _distribution(clean_df["willingness_to_call"], n, range(11)),
    }


def summarize_missingness(clean_df: pd.DataFrame) -> list[dict]:
    """Separate original blanks from invalid/unusable answers after cleaning."""
    rows = []
    for column in EXPECTED_COLUMNS:
        original = clean_df[f"{column}_raw"]
        # Use exactly the same blank/Unicode rules as cleaning.py.
        source_missing = int(original.map(normalize_source_text).isna().sum())
        missing = int(clean_df[column].isna().sum())
        rows.append({
            "field": column, "denominator_rows": len(clean_df),
            "source_missing_n": source_missing,
            "invalid_or_unusable_n": missing - source_missing,
            "missing_or_invalid_n": missing,
            "usable_n": int(clean_df[column].notna().sum()),
            "missing_or_invalid_share": _rate(missing, len(clean_df)),
        })
    return sorted(rows, key=lambda row: row["missing_or_invalid_n"], reverse=True)


def _groups(clean_df, field):
    if field == "role":
        roles = sorted({r for roles in clean_df["role_list"] for r in roles})
        for role in roles:
            yield role, clean_df.loc[clean_df["role_list"].map(lambda roles: role in roles)]
    else:
        for category, group in clean_df.groupby(field, dropna=True, sort=True):
            yield str(category), group


def summarize_coverage(clean_df: pd.DataFrame, min_group_n=DEFAULT_MIN_GROUP_N) -> dict:
    """Participation counts and willingness answer coverage; no group ranking."""
    _check_min_n(min_group_n)
    result = {}
    for field in ["county", "role", "language"]:
        records = []
        for category, group in _groups(clean_df, field):
            n = len(group)
            valid = int(group["willingness_to_call"].notna().sum())
            records.append({
                "category": category, "n": n,
                "denominator_rows": len(clean_df),
                "share_of_rows": _rate(n, len(clean_df)),
                "small_group": n < min_group_n,
                "willingness_valid_n": valid,
                "willingness_missing_or_invalid_n": n - valid,
                "willingness_response_rate": _rate(valid, n),
            })
        missing = (int(clean_df["role_list"].map(len).eq(0).sum())
                   if field == "role" else int(clean_df[field].isna().sum()))
        result[field] = {"missing_category_n": missing, "groups": records}
    result["training_date"] = {
        "missing_or_invalid_n": int(clean_df["training_date"].isna().sum()),
        "denominator_rows": len(clean_df),
        "dates": [
            {"date": day.isoformat(), "n": int(n), "small_group": int(n) < min_group_n}
            for day, n in clean_df["training_date"].dt.normalize().value_counts().sort_index().items()
        ],
    }
    return result


def summarize_group_comparisons(clean_df: pd.DataFrame, min_group_n=DEFAULT_MIN_GROUP_N) -> dict:
    """Suppress knowledge comparisons when the valid paired n is too small.

    Evaluate each topic's paired n independently, not just the group's row count.
    """
    _check_min_n(min_group_n)
    result = {}
    hidden_fields = [
        "before_mean", "after_mean", "mean_change", "count_up", "count_same",
        "count_down", "share_up", "share_same", "share_down",
    ]
    for field in ["county", "role", "language"]:
        result[field] = []
        for category, group in _groups(clean_df, field):
            knowledge = summarize_knowledge(group)
            for stats in [*knowledge["topics"].values(), knowledge["overall_three_topic_mean"]]:
                stats["suppressed"] = stats["n"] < min_group_n
                if stats["suppressed"]:
                    for key in hidden_fields:
                        stats[key] = None
            result[field].append({"category": category, "n": len(group), "knowledge": knowledge})
    return result


def filter_survey(clean_df, *, counties=None, roles=None, languages=None,
                  start_date=None, end_date=None):
    """AND across filters; OR within selections. None/[] means all categories.

    Role selection checks membership and never duplicates survey rows.
    Unknown dates remain included unless a date bound is selected.
    """
    mask = pd.Series(True, index=clean_df.index)
    if counties:
        mask &= clean_df["county"].isin(counties)
    if roles:
        selected = set(roles)
        mask &= clean_df["role_list"].map(lambda values: bool(selected.intersection(values)))
    if languages:
        mask &= clean_df["language"].isin(languages)
    if start_date is not None:
        mask &= clean_df["training_date"].ge(pd.Timestamp(start_date).normalize())
    if end_date is not None:
        mask &= clean_df["training_date"].lt(pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1))
    return clean_df.loc[mask].copy(deep=True)


def build_summary(clean_df: pd.DataFrame, min_group_n=DEFAULT_MIN_GROUP_N) -> dict:
    """Recompute every dashboard metric from the same full or filtered frame."""
    _check_min_n(min_group_n)
    n = len(clean_df)
    roles = {role for values in clean_df["role_list"] for role in values}
    willingness_n = int(clean_df["willingness_to_call"].notna().sum())
    return {
        "pipeline_version": PIPELINE_VERSION,
        "cleaning_version": CLEANING_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "min_group_n": min_group_n,
        "share_units": "fraction_0_to_1",
        "overview": {
            "survey_rows": n,
            "distinct_nonmissing_ids": int(clean_df["id"].nunique()),
            "distinct_training_dates": int(clean_df["training_date"].nunique()),
            "fully_paired_knowledge_rows": int(clean_df[KNOWLEDGE_COLUMNS].notna().all(axis=1).sum()),
            "willingness_valid_n": willingness_n,
            "willingness_missing_or_invalid_n": n - willingness_n,
            "willingness_response_rate": _rate(willingness_n, n),
            "county_count": int(clean_df["county"].nunique()),
            "role_category_count": len(roles),
            "total_role_selections": sum(map(len, clean_df["role_list"])),
        },
        "knowledge": summarize_knowledge(clean_df),
        "distributions": summarize_distributions(clean_df),
        "coverage": summarize_coverage(clean_df, min_group_n),
        "missingness": summarize_missingness(clean_df),
        "group_comparisons": summarize_group_comparisons(clean_df, min_group_n),
        "limitations": list(LIMITATIONS),
    }


def export_summary(clean_df, output_path, min_group_n=DEFAULT_MIN_GROUP_N):
    """Write an aggregate-only JSON summary computed from the cleaned frame.

    No participant-level export is provided. This does not anonymize small cells.
    """
    path = Path(output_path)
    if path.suffix.lower() != ".json":
        raise ValueError("Choose a .json path for the aggregate summary.")
    summary = build_summary(clean_df, min_group_n)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return path


def run_pipeline(source, sheet_name="Survey Data", min_group_n=DEFAULT_MIN_GROUP_N) -> PipelineResult:
    """Load -> validate -> clean -> quality report -> shared dashboard summaries."""
    _check_min_n(min_group_n)
    raw_df = load_survey(source, sheet_name=sheet_name)
    clean_df, audit = clean_survey(raw_df)
    quality = summarize_quality(clean_df, audit)
    summary = build_summary(clean_df, min_group_n)
    summary["quality"] = quality
    return PipelineResult(raw_df, clean_df, audit, quality, summary)


def main():
    parser = argparse.ArgumentParser(description="Build shared survey statistics.")
    parser.add_argument("workbook", help="Path to the survey Excel file")
    parser.add_argument("--sheet", default="Survey Data")
    parser.add_argument("--min-group-n", type=int, default=DEFAULT_MIN_GROUP_N)
    parser.add_argument("--export", metavar="FILE.json", help="Optional aggregate-only export")
    args = parser.parse_args()
    try:
        result = run_pipeline(args.workbook, args.sheet, args.min_group_n)
        print(json.dumps({"overview": result.summary["overview"],
                          "knowledge": result.summary["knowledge"],
                          "invalid_values": result.audit["invalid_values"],
                          "date_failures": result.audit["date_failures"],
                          "duplicate_ids": result.audit["duplicate_ids"]}, indent=2, allow_nan=False))
        if args.export:
            path = export_summary(result.clean_df, args.export, args.min_group_n)
            print(f"Aggregate summary written to {path}")
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(status=1, message=f"Unable to process workbook: {exc}\n")


if __name__ == "__main__":
    main()
