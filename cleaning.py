"""Beyond Awareness survey loading, validation, cleaning, and quality checks.

Requires pandas and openpyxl. Does not print, save, or export participant data.
Keep the dataframe returned by load_survey as your untouched raw copy.
The cleaned dataframe still contains sensitive text; do not publish it.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import re
import unicodedata

import pandas as pd


CLEANING_VERSION = "1.0.0"

# Headers verified against the supplied workbook. Matching ignores whitespace,
# case, and Unicode formatting marks, but never guesses columns by position.
SOURCE_HEADERS = [
    "Id",
    "Start time",
    "Completion time",
    "Language",
    "Are you a....?",
    "Please enter the date of your training.",
    "Which county is this training affiliated with?",
    "Please tell us how much you disagree or agree with the statements..I can identify mental health challenges and crises.",
    "Please tell us how much you disagree or agree with the statements..I can describe 988 and how it works.",
    "Please tell us how much you disagree or agree with the statements..I know when to use 988.",
    "Now think back to before you took part in the Understanding 988 training.  .I could identify mental health challenges and crises.",
    "Now think back to before you took part in the Understanding 988 training.  .I could describe 988 and how it works.",
    "Now think back to before you took part in the Understanding 988 training.  .I knew when to use 988.",
    "How much do you agree or disagree with the following aspects of the training?.The presenter(s) engaged the participants.",
    "How much do you agree or disagree with the following aspects of the training?.The presenter(s) knew the subject matter well.",
    "How much do you agree or disagree with the following aspects of the training?.The training was well organized.",
    "How likely are you to recommend the Understanding 988 training to a friend or colleague?",
    "How likely are you to call 988 if you or someone else is experiencing a mental health challenge or crisis?",
    "What was the most valuable thing you learned during the training?",
    "How can we improve this training in the future?",
]

EXPECTED_COLUMNS = [
    "id", "start_time", "completion_time", "language", "participant_type",
    "training_date", "county", "after_identify", "after_describe", "after_when",
    "before_identify", "before_describe", "before_when", "presenter_engagement",
    "presenter_expertise", "training_organization", "recommend_training",
    "willingness_to_call", "valuable_feedback", "improvement_feedback",
]

PAIRS = {
    "Identify crisis": ("before_identify", "after_identify"),
    "Describe 988": ("before_describe", "after_describe"),
    "Know when to use 988": ("before_when", "after_when"),
}
KNOWLEDGE_COLUMNS = [column for pair in PAIRS.values() for column in pair]
PRESENTER_COLUMNS = [
    "presenter_engagement", "presenter_expertise", "training_organization",
]
LIKERT_MAP = {
    "strongly disagree": 1,
    "disagree": 2,
    "neither agree nor disagree": 3,
    "agree": 4,
    "strongly agree": 5,
}
COUNTY_MAP = {
    "anne arundel": "Anne Arundel",
    "anne arundel county": "Anne Arundel",
    "prince george's": "Prince George's",
    "prince george's county": "Prince George's",
    "montgomery": "Montgomery",
    "montgomery county": "Montgomery",
    "montgomery county with nami mc": "Montgomery",
    "queen anne's": "Queen Anne's",
    "queen anne's county": "Queen Anne's",
    "fairfax": "Fairfax",
    "fairfax county": "Fairfax",
    "harris": "Harris",
    "harris county": "Harris",
}
ROLE_MAP = {
    "student": "Student",
    "school staff": "School staff",
    "school staff member": "School staff",
    "caregiver/parent": "Caregiver/parent",
    "community member": "Community member",
    "other (e.g., community member)": "Community member",
    "other/unclassified": "Other/unclassified",
    "other": "Other/unclassified",
}
LANGUAGE_MAP = {
    "english (united states)": "English",
    "english": "English",
    "español (méxico)": "Spanish",
    "español": "Spanish",
    "spanish": "Spanish",
}


def _text(value):
    """Normalize scalar text; blanks become NA, not a string like 'nan'."""
    if pd.isna(value):
        return pd.NA
    text = unicodedata.normalize("NFKC", str(value))
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else pd.NA


def _key(value):
    text = _text(value)
    return "" if pd.isna(text) else text.casefold()


def validate_schema(raw_df: pd.DataFrame) -> dict:
    """Return a schema report. load_survey/clean_survey raise if invalid.

    Both the verified original headers and the team's exact 20-column contract
    are accepted. Column order may change. Extra/missing/duplicate headers fail.
    """
    if not isinstance(raw_df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    original = dict(zip(map(_key, SOURCE_HEADERS), EXPECTED_COLUMNS))
    contract = {_key(c): c for c in EXPECTED_COLUMNS}
    mapping = {**original, **contract}
    resolved = [mapping.get(_key(c)) for c in raw_df.columns]
    counts = pd.Series([c for c in resolved if c is not None]).value_counts()
    missing = [c for c in EXPECTED_COLUMNS if c not in resolved]
    # Positions avoid echoing arbitrary uploaded headers into public logs.
    unexpected = [i + 1 for i, c in enumerate(resolved) if c is None]
    duplicates = [str(c) for c, n in counts.items() if n > 1]
    valid = not missing and not unexpected and not duplicates
    return {
        "valid": valid,
        "row_count": len(raw_df),
        "column_count": len(raw_df.columns),
        "missing_columns": missing,
        "unexpected_column_positions": unexpected,
        "duplicate_columns": duplicates,
        "resolved_columns": resolved,
    }


def _require_schema(raw_df):
    report = validate_schema(raw_df)
    if not report["valid"]:
        raise ValueError(
            "Survey schema mismatch. "
            f"Missing columns: {report['missing_columns']}; "
            f"unrecognized column positions: {report['unexpected_column_positions']}; "
            f"duplicate columns: {report['duplicate_columns']}. "
            "Expected the 20 survey questions or their shared contract names."
        )
    return report


def load_survey(source, sheet_name="Survey Data") -> pd.DataFrame:
    """Read an Excel path/file-like object, validate it, and retain raw values.

    dtype=object avoids forcing IDs into numeric columns. keep_default_na=False
    preserves literal responses such as 'NA'; actual blanks are handled later.
    A source can be a path, BytesIO, or a Streamlit UploadedFile.
    """
    raw_df = pd.read_excel(
        source, sheet_name=sheet_name, dtype=object, keep_default_na=False,
        engine="openpyxl",
    )
    _require_schema(raw_df)
    return raw_df


def normalize_county(value):
    """Normalize known training affiliations; preserve unknown text and blanks."""
    text = _text(value)
    if pd.isna(text):
        return pd.NA
    return COUNTY_MAP.get(_key(text), text)


def parse_roles(value) -> list[str]:
    """Split semicolon selections, normalize, and deduplicate within each row.

    Blank roles become []; unknown selections become Other/unclassified.
    The original selection is preserved separately by clean_survey.
    """
    text = _text(value)
    if pd.isna(text):
        return []
    roles = []
    for token in text.split(";"):
        if _key(token):
            role = ROLE_MAP.get(_key(token), "Other/unclassified")
            if role not in roles:
                roles.append(role)
    return roles


def _parse_date(value):
    if pd.isna(_text(value)):
        return pd.NaT
    # Reject bare numbers: pandas otherwise treats them as nanoseconds since 1970.
    # Excel dates stored as actual dates are read as datetime objects.
    if not isinstance(value, (str, datetime, date, pd.Timestamp)):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce")


def clean_survey(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return a separate cleaned dataframe and aggregate quality audit.

    No imputation, row deletion, deduplication, or rating clipping is performed.
    Each original field is retained as <column>_raw; role_raw is an alias.
    Rating invalid flags distinguish nonresponses from unusable answers.
    Date strings are interpreted by pandas (month-first for ambiguous US dates).
    """
    schema = _require_schema(raw_df)
    df = raw_df.copy(deep=True)
    df.columns = schema["resolved_columns"]
    for column in EXPECTED_COLUMNS:
        df[f"{column}_raw"] = df[column].copy(deep=True)
        df[column] = df[column].map(_text)

    audit = {
        "cleaning_version": CLEANING_VERSION,
        "original_row_count": len(raw_df),
        "schema": schema,
        "invalid_values": {},
        "unmapped_categories": {},
        "date_failures": {},
        "normalization_counts": {},
        "assumptions": [
            "County is training affiliation, not participant residence.",
            "Other (e.g., community member) is grouped as Community member.",
            "Role counts count each survey row once per selected role.",
            "Repeated IDs are flagged and retained; rows may not be unique people.",
            "Ambiguous text dates use month-first interpretation; numeric dates fail.",
            "Knowledge ratings are retrospective ordinal self-reports, not causal evidence.",
        ],
    }

    for column in KNOWLEDGE_COLUMNS + PRESENTER_COLUMNS:
        mapping = dict(LIKERT_MAP)
        if column in PRESENTER_COLUMNS:
            mapping["neither agree or disagree"] = 3
        keys = df[column].map(_key)
        scored = keys.map(mapping).astype("Int64")
        invalid = df[column].notna() & scored.isna()
        df[f"{column}_invalid"] = invalid
        # Only fixed rating categories are exposed here; unusual text is private.
        audit["unmapped_categories"][column] = {
            "count": int(invalid.sum()),
            "very_agree": int((keys == "very agree").sum()),
            "satisfied": int((keys == "satisfied").sum()),
            "other": int((invalid & ~keys.isin(["very agree", "satisfied"])).sum()),
        }
        audit["invalid_values"][column] = int(invalid.sum())
        df[column] = scored

    for column in ["recommend_training", "willingness_to_call"]:
        numeric = pd.to_numeric(df[column], errors="coerce").astype("Float64")
        # Booleans are not legitimate numeric survey answers.
        is_bool = df[f"{column}_raw"].map(lambda v: isinstance(v, bool))
        invalid = df[column].notna() & (
            numeric.isna() | ~numeric.between(0, 10).fillna(False) | is_bool
        )
        df[f"{column}_invalid"] = invalid.astype(bool)
        df[column] = numeric.mask(invalid)
        audit["invalid_values"][column] = int(invalid.sum())

    df["county"] = df["county"].map(normalize_county)
    df["county_unmapped"] = df["county"].notna() & ~df["county"].isin(COUNTY_MAP.values())
    audit["unmapped_categories"]["county"] = int(df["county_unmapped"].sum())

    df["role_raw"] = df["participant_type_raw"].copy(deep=True)
    role_text = df["participant_type"].copy()
    df["role_list"] = role_text.map(parse_roles)
    df["participant_type"] = df["role_list"].map(
        lambda roles: "; ".join(roles) if roles else pd.NA
    )
    df["role_unmapped"] = role_text.map(
        lambda value: any(
            _key(t) not in ROLE_MAP for t in str(value).split(";") if _key(t)
        ) if pd.notna(value) else False
    )
    audit["unmapped_categories"]["role_rows"] = int(df["role_unmapped"].sum())

    df["language"] = df["language"].map(
        lambda value: LANGUAGE_MAP.get(_key(value), value)
    )
    df["language_unmapped"] = df["language"].notna() & ~df["language"].isin(LANGUAGE_MAP.values())
    audit["unmapped_categories"]["language"] = int(df["language_unmapped"].sum())

    for column in ["start_time", "completion_time", "training_date"]:
        present = df[column].notna()
        parsed = df[f"{column}_raw"].map(_parse_date)
        # Preserve local clock times; mixed timezones should be resolved explicitly
        # before using this dataset for date filtering.
        try:
            parsed = pd.to_datetime(parsed, errors="coerce")
            if column == "training_date":
                parsed = parsed.dt.normalize()
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Inconsistent timezone formats in {column}.") from exc
        df[f"{column}_invalid"] = present & parsed.isna()
        audit["date_failures"][column] = int(df[f"{column}_invalid"].sum())
        df[column] = parsed

    for column in ["county", "participant_type", "language"]:
        original = df[f"{column}_raw"]
        changed = [
            False if pd.isna(_text(old)) else str(old) != str(new)
            for old, new in zip(original, df[column])
        ]
        audit["normalization_counts"][column] = sum(changed)

    df["duplicate_id"] = df["id"].notna() & df["id"].duplicated(keep=False)
    audit["duplicate_ids"] = {
        "rows_with_duplicate_id": int(df["duplicate_id"].sum()),
        "distinct_duplicate_ids": int(df.loc[df["duplicate_id"], "id"].nunique()),
        "extra_rows_beyond_first": int(
            (df["id"].notna() & df["id"].duplicated()).sum()
        ),
        "missing_id_rows": int(df["id"].isna().sum()),
    }
    # Metrics use these masks later; an overall score needs all six answers.
    for topic, (before, after) in PAIRS.items():
        suffix = before.removeprefix("before_")
        df[f"paired_{suffix}"] = df[[before, after]].notna().all(axis=1)
    df["paired_all_knowledge"] = df[KNOWLEDGE_COLUMNS].notna().all(axis=1)
    audit["missingness"] = {
        column: {
            "source_missing": int(df[f"{column}_raw"].map(_text).isna().sum()),
            "clean_missing": int(df[column].isna().sum()),
        }
        for column in EXPECTED_COLUMNS
    }
    return df, audit


def summarize_quality(clean_df: pd.DataFrame, audit: dict) -> dict:
    """Return JSON-compatible aggregate diagnostics, without IDs or comments.

    Pass the full dataframe produced by clean_survey. For a filtered dataset,
    rerun cleaning on its raw rows to obtain a matching audit first.
    """
    if len(clean_df) != audit["original_row_count"]:
        raise ValueError("Quality summary requires the dataframe matching this audit.")
    n = len(clean_df)
    dates = clean_df["training_date"].dropna()
    result = deepcopy(audit)
    result.update({
        "clean_row_count": n,
        "distinct_nonmissing_ids": int(clean_df["id"].nunique()),
        "distinct_training_dates": int(dates.nunique()),
        "training_date_range": {
            "start": dates.min().isoformat() if len(dates) else None,
            "end": dates.max().isoformat() if len(dates) else None,
        },
        "fully_paired_knowledge_rows": int(clean_df["paired_all_knowledge"].sum()),
        "paired_rows_by_topic": {
            topic: int(clean_df[[before, after]].notna().all(axis=1).sum())
            for topic, (before, after) in PAIRS.items()
        },
        "willingness_valid_rows": int(clean_df["willingness_to_call"].notna().sum()),
        "willingness_response_rate": (
            float(clean_df["willingness_to_call"].notna().mean()) if n else None
        ),
        "county_count": int(clean_df["county"].nunique()),
        "role_category_count": int(clean_df["role_list"].explode().dropna().nunique()),
        "total_role_selections": int(clean_df["role_list"].map(len).sum()),
        "denominator_rows": n,
    })
    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate and clean a survey workbook.")
    parser.add_argument("workbook", help="Path to the survey Excel file")
    parser.add_argument("--sheet", default="Survey Data", help="Worksheet name")
    args = parser.parse_args()
    try:
        raw = load_survey(args.workbook, sheet_name=args.sheet)
        cleaned, cleaning_audit = clean_survey(raw)
        # Aggregate diagnostics only; never print participant records or comments.
        print(json.dumps(summarize_quality(cleaned, cleaning_audit), indent=2))
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(status=1, message=f"Unable to process workbook: {exc}\n")
