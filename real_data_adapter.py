import io
import re

import pandas as pd

SMALL_GROUP_THRESHOLD = 30

# Words in the survey -> numbers. Change here if the team picks a different scale.
LIKERT = {
    "strongly disagree": 1,
    "disagree": 2,
    "neither agree nor disagree": 3,
    "agree": 4,
    "strongly agree": 5,
}

# The three knowledge statements: (name shown in the report, keyword to find the column)
KNOWLEDGE_ITEMS = [
    ("Identify mental health challenges and crises", "identify"),
    ("Describe 988 and how it works", "describe 988"),
    ("Know when to use 988", "when to use"),
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _clean(value):
    """Turn any cell into tidy text: removes hidden characters and extra spaces. Blank/NaN -> ''."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).replace("\xa0", " ").replace("\u200e", "").replace("\u200f", "")
    return re.sub(r"\s+", " ", text).strip()


def _find_col(df, contains=(), startswith=None, exact=None):
    """Find the first column whose cleaned, lower-case name matches. Returns the column name or None."""
    for col in df.columns:
        name = _clean(col).lower()
        if exact is not None and name != exact:
            continue
        if startswith is not None and not name.startswith(startswith):
            continue
        if all(word in name for word in contains):
            return col
    return None


def _likert(value):
    """'Strongly agree ' -> 5 (and so on). Anything else -> NaN."""
    return LIKERT.get(_clean(value).lower(), float("nan"))


def _canon_county(value):
    """Fix messy county names ('Montgomery County with NAMI MC' -> 'Montgomery')."""
    text = _clean(value).lower()
    if not text:
        return "Not provided"
    if "anne arundel" in text:
        return "Anne Arundel"
    if "prince george" in text:
        return "Prince George's"
    if "montgomery" in text:
        return "Montgomery"
    if "queen anne" in text:
        return "Queen Anne's"
    if "fairfax" in text:
        return "Fairfax"
    return "Other / unclear"


def _counts(labels):
    """Count labels -> plain dict {label: int}, biggest first."""
    series = pd.Series(list(labels))
    return {str(k): int(v) for k, v in series.value_counts().items()}


def _finding(id_, type_, title, description, count, denominator, limitations, evidence, source, status):
    """Build one finding dict with the standard fields (plain Python numbers only)."""
    count = None if count is None else int(count)
    denominator = None if denominator is None else int(denominator)
    pct = round(100.0 * count / denominator, 1) if (count is not None and denominator) else None
    return {"id": id_, "source": source, "type": type_, "title": title, "description": description,
            "count": count, "denominator": denominator, "percentage": pct,
            "limitations": limitations, "evidence": evidence, "status": status}


# ---------------------------------------------------------------------------
# Reading the file
# ---------------------------------------------------------------------------
def load_survey(source):
    """Read the CSV from a file path OR an uploaded file object. Returns a DataFrame."""
    if hasattr(source, "read"):
        raw = source.read()
    else:
        with open(source, "rb") as handle:
            raw = handle.read()
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raw = raw.decode("latin-1")
    return pd.read_csv(io.StringIO(raw))


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def build_real_inputs(df):
    """Turn the survey DataFrame into (findings, metrics, summary). See file header."""
    if df is None or len(df) == 0:
        raise ValueError("The survey file has no rows.")
    total = int(len(df))

    # ---- find the columns we need (by keywords, so small header changes do not break it) ----
    col_id = _find_col(df, exact="id")
    col_lang = _find_col(df, contains=["language"])
    col_role = _find_col(df, contains=["are you a"])
    col_date = _find_col(df, contains=["date of your training"])
    col_county = _find_col(df, contains=["county"])
    col_call = _find_col(df, contains=["likely are you to call 988"])
    col_start = _find_col(df, exact="start time")

    notes = []   # plain-language data-quality notes for the summary

    # ---- Training outcomes: recalled-before vs current, PAIRED rows only ----
    knowledge = []
    for name, keyword in KNOWLEDGE_ITEMS:
        cur_col = _find_col(df, contains=[keyword], startswith="please tell us how much")
        bef_col = _find_col(df, contains=[keyword], startswith="now think back")
        if cur_col is None or bef_col is None:
            notes.append("Could not find both columns for: " + name)
            continue
        current = df[cur_col].map(_likert)
        before = df[bef_col].map(_likert)
        paired = current.notna() & before.notna()
        n_paired = int(paired.sum())
        knowledge.append({
            "measure": name,
            "before_mean": round(float(before[paired].mean()), 2) if n_paired else None,
            "current_mean": round(float(current[paired].mean()), 2) if n_paired else None,
            "n_paired": n_paired,
        })

    # ---- Call-intent coverage ----
    findings = []
    call_info = {"n_answered": None, "n_total": total}
    by_month = {}
    if col_call is not None:
        call = pd.to_numeric(df[col_call], errors="coerce")
        answered_mask = call.notna()
        n_answered = int(answered_mask.sum())
        call_info = {"n_answered": n_answered, "n_total": total}

        if col_start is not None:
            months = pd.to_datetime(df[col_start], errors="coerce").dt.strftime("%Y-%m")
            frame = pd.DataFrame({"month": months, "answered": answered_mask}).dropna(subset=["month"])
            for month, group in frame.groupby("month"):
                by_month[str(month)] = {"answered": int(group["answered"].sum()), "total": int(len(group))}
        zero_months = sorted(m for m, v in by_month.items() if v["total"] >= 5 and v["answered"] == 0)

        limits = ["Descriptive count from the uploaded CSV; not interpreted",
                  "Reason for blank answers is unknown"]
        if zero_months:
            limits.append("Blanks are NOT evenly spread: no answers at all in these months: %s "
                          "(the question may have been missing from some survey versions - not confirmed)"
                          % ", ".join(zero_months))
        findings.append(_finding(
            "real_001", "low_call_intent_response_rate",
            "Call-intent question left blank by most responses",
            "%d of %d responses have no answer to 'How likely are you to call 988...' (%d answered)."
            % (total - n_answered, total, n_answered),
            total - n_answered, total, limits,
            {"answered_by_month": by_month}, "real_data_adapter", "descriptive"))
    else:
        notes.append("Could not find the call-intent column.")

    # ---- Group sizes (counts only) ----
    county_counts, role_counts, language_counts = {}, {}, {}
    if col_county is not None:
        county_counts = _counts(df[col_county].map(_canon_county))
    if col_lang is not None:
        language_counts = _counts(df[col_lang].map(_clean).replace("", "Not provided"))
    if col_role is not None:
        roles = []
        for cell in df[col_role]:
            roles += [r.strip() for r in _clean(cell).split(";") if r.strip()]
        role_counts = _counts(roles)      # people can pick several roles, so these overlap

    for number, (label, counts, kind) in enumerate(
            [("county", county_counts, "county"), ("language", language_counts, "language")], start=2):
        small = {k: v for k, v in counts.items() if v < SMALL_GROUP_THRESHOLD and k != "Not provided"}
        if small:
            listing = ", ".join("%s (n=%d)" % (k, v) for k, v in small.items())
            findings.append(_finding(
                "real_00%d" % number, "small_group_sample",
                "Very small %s groups" % label,
                "These %s groups have fewer than %d responses: %s." % (label, SMALL_GROUP_THRESHOLD, listing),
                sum(small.values()), total,
                ["Descriptive count from the uploaded CSV; not interpreted",
                 "The cut-off of %d is a team choice (SMALL_GROUP_THRESHOLD)" % SMALL_GROUP_THRESHOLD,
                 "Group differences here should not be over-interpreted"],
                {"groups": small, "threshold": SMALL_GROUP_THRESHOLD}, "real_data_adapter", "descriptive"))

    # ---- Survey design facts (measurement gaps), checked against the column names ----
    headers = " | ".join(_clean(c).lower() for c in df.columns)
    if col_call is not None and not re.search(r"\b(text|chat)\b", headers):
        findings.append(_finding(
            "real_005", "communication_measurement_gap",
            "Survey asks only about willingness to call 988",
            "No survey column mentions texting or chatting, so contact-method preferences are not measured.",
            None, None, ["This is a measurement gap, not a participant result"], {},
            "real_data_adapter", "measurement_gap"))
    if not re.search(r"privacy|confidential|trust|police", headers):
        findings.append(_finding(
            "real_006", "privacy_measurement_gap",
            "Privacy and trust are not measured",
            "No survey column asks about privacy, confidentiality, or trust.",
            None, None, ["Trust is not measured; do not claim a trust problem"], {},
            "real_data_adapter", "measurement_gap"))
    if any(_clean(c).lower().startswith("now think back") for c in df.columns) and not re.search(r"follow[- ]?up", headers):
        findings.append(_finding(
            "real_007", "immediate_only_measurement",
            "Knowledge is measured only right after training",
            "'Before' ratings are recalled after the training and there is no later follow-up.",
            None, None, ["Retrospective self-report", "No follow-up data"], {},
            "real_data_adapter", "measurement_gap"))

    # ---- Dataset period and missing data notes ----
    period = None
    if col_date is not None:
        dates = pd.to_datetime(df[col_date], errors="coerce")
        if dates.notna().any():
            period = "%s to %s" % (dates.min().strftime("%b %d, %Y"), dates.max().strftime("%b %d, %Y"))
        missing_dates = int(dates.isna().sum())
        if missing_dates:
            notes.append("%d row(s) have no usable training date." % missing_dates)

    metrics = {
        "status": "real",
        "dataset_period": period,
        "n_responses": total,
        "responses_verified": bool(col_id is not None and df[col_id].is_unique),
        "scale_note": "Ratings converted from words to numbers: Strongly disagree=1, Disagree=2, "
                      "Neither=3, Agree=4, Strongly agree=5. Means use paired rows only.",
        "scale_max": 5,
        "knowledge": knowledge,
        "call_intent": call_info,
        # Left out on purpose: knowledge_call_relationship (Person 2) and themes (Person 3).
        "themes": [],
        "approved_excerpts": [],
    }

    summary = {"n_rows": total, "counties": county_counts, "roles": role_counts,
               "languages": language_counts, "call_intent_by_month": by_month, "notes": notes}
    return findings, metrics, summary


def load_and_build(source):
    """Convenience: read the CSV (path or uploaded file) and build everything."""
    return build_real_inputs(load_survey(source))