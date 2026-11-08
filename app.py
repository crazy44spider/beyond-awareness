"""Beyond Awareness app. Start with: python -m streamlit run app.py

Keep app.py, dashboard.py, cleaning.py, and pipeline.py together.
Install: python -m pip install pandas openpyxl streamlit plotly pytest

Optional teammate contracts (pure functions, no Streamlit side effects):
    gap_detector.analyze_gaps(clean_df) -> {"findings": [finding, ...]}
    qualitative.analyze_feedback(clean_df) -> {"findings": [finding, ...]}
    accessibility.audit_survey(clean_df) -> {"findings": [finding, ...]}
    interventions.recommend_interventions(findings) -> {"findings": [finding, ...]}
    report_generator.generate_report(metrics=..., findings=..., selections=...) -> PDF bytes

finding fields: id, source, type, title, description, count, denominator,
percentage (0-100 or None), limitations (list[str]), evidence (dict).
Only validated aggregate findings should enter this contract. No respondent
quotes, names, or identifying evidence. Adapt MODULES when teammates choose
different names. Missing modules show 'Feature in progress'; broken modules
show an explicit error without exposing their exception contents or raw data.

Real workbooks are kept only in the session, never in a global data cache or
written to disk. Use real data only in an approved local/private environment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib
from io import BytesIO
import json
import math
from numbers import Real
import random

import pandas as pd
import streamlit as st

from cleaning import EXPECTED_COLUMNS, KNOWLEDGE_COLUMNS, clean_survey, summarize_quality
from pipeline import PipelineResult, build_summary, filter_survey, run_pipeline
from dashboard import render_dashboard, render_quality, style_app
from person4.survey_designer import analyze_survey, render_survey_designer
from team_integration import render_gap_detector, render_action_lab, render_pdf_report

PAGES = ["Overview", "Gap Detector", "Participant Voices", "Accessibility Audit", "Action Lab", "Report"]
MODULES = {
    "Gap Detector": ("gap_detector", "analyze_gaps"),
    "Participant Voices": ("qualitative", "analyze_feedback"),
    "Accessibility Audit": ("accessibility", "audit_survey"),
    "Action Lab": ("interventions", "recommend_interventions"),
    "Report": ("report_generator", "generate_report"),
}


def make_demo_data(rows=180):
    """Fixed synthetic examples. Never derived from actual survey records."""
    rng = random.Random(988)
    likert = {1: "Strongly disagree", 2: "Disagree", 3: "Neither agree nor disagree", 4: "Agree", 5: "Strongly agree"}
    records = []
    for i in range(rows):
        row = dict.fromkeys(EXPECTED_COLUMNS, "")
        day = datetime(2026, 1, 5) + timedelta(days=(i % 6) * 7)
        row.update(
            id=f"DEMO-{i + 1:04d}", start_time=day.isoformat(),
            completion_time=(day + timedelta(minutes=4)).isoformat(), training_date=day.date().isoformat(),
            language="Spanish" if i % 13 == 0 else "English",
            county=["Anne Arundel", "Prince George's", "Montgomery", "Fairfax"][i % 4],
            participant_type=["Student", "School staff member", "Caregiver/parent", "Other (e.g., community member)"][i % 4],
            presenter_engagement="Very agree" if i % 19 == 0 else rng.choice(["Agree", "Strongly agree"]),
            presenter_expertise="Satisfied" if i % 23 == 0 else rng.choice(["Agree", "Strongly agree"]),
            training_organization=rng.choice(["Agree", "Strongly agree", "Neither agree or disagree"]),
            recommend_training=rng.randint(4, 10),
            willingness_to_call=rng.randint(0, 10) if i % 4 == 0 else "",
        )
        if i % 10 == 0:
            row["participant_type"] += ";Caregiver/parent"
        for topic in ["identify", "describe", "when"]:
            before = rng.randint(1, 5)
            after = max(1, min(5, before + rng.choice([-1, 0, 1, 1, 2])))
            row[f"before_{topic}"] = likert[before]
            row[f"after_{topic}"] = likert[after]
        if i % 17 == 0:
            row["before_describe"] = ""
        if i % 41 == 0:
            row["training_date"] = "invalid demo date"
        records.append(row)
    return pd.DataFrame(records, columns=EXPECTED_COLUMNS)


@st.cache_data(show_spinner=False)
def demo_result():
    """Only synthetic data uses a shared cache."""
    raw = make_demo_data()
    clean, audit = clean_survey(raw)
    quality = summarize_quality(clean, audit)
    summary = build_summary(clean)
    summary["quality"] = quality
    return PipelineResult(raw, clean, audit, quality, summary)


def load_optional_module(page):
    """Return (callable, status); distinguish absent modules from broken imports."""
    module_name, function_name = MODULES[page]
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None, "missing"
        return None, "broken"
    except Exception:
        return None, "broken"
    function = getattr(module, function_name, None)
    return (function, "ready") if callable(function) else (None, "contract_error")


def validate_findings(payload):
    """Validate the common finding schema; return only display-approved fields."""
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise ValueError("Expected a dictionary with a findings list.")
    result, seen = [], set()
    for finding in payload["findings"]:
        if not isinstance(finding, dict):
            raise ValueError("Every finding must be a dictionary.")
        item = {}
        for field in ["id", "source", "type", "title", "description"]:
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Finding text fields must be nonempty strings.")
            item[field] = value
        if item["id"] in seen:
            raise ValueError("Finding IDs must be unique within a module.")
        seen.add(item["id"])
        for field in ["count", "denominator", "percentage"]:
            value = finding.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0):
                raise ValueError("Finding metrics must be finite nonnegative numbers or None.")
            item[field] = value
        if item["percentage"] is not None and item["percentage"] > 100:
            raise ValueError("Finding percentage must be between 0 and 100.")
        if item["count"] is not None and item["denominator"] is not None and item["count"] > item["denominator"]:
            raise ValueError("Finding count cannot exceed its denominator.")
        limits = finding.get("limitations")
        if not isinstance(limits, list) or not all(isinstance(v, str) for v in limits):
            raise ValueError("Finding limitations must be a list of strings.")
        if not isinstance(finding.get("evidence"), dict):
            raise ValueError("Finding evidence must be a dictionary.")
        item["limitations"] = limits
        # Evidence is deliberately not displayed or forwarded into public reports.
        item["evidence"] = {}
        result.append(item)
    return result


def collect_findings(clean_df):
    """Ask available analysis modules for aggregates; surface failed dependencies."""
    findings, issues = [], []
    for page in ["Gap Detector", "Participant Voices", "Accessibility Audit"]:
        function, status = load_optional_module(page)
        if status == "missing":
            continue
        if status != "ready":
            issues.append(f"{page}: module is present but unavailable ({status}).")
            continue
        try:
            findings.extend(validate_findings(function(clean_df.copy(deep=True))))
        except Exception:
            issues.append(f"{page}: analysis failed or returned an invalid finding structure.")
    return findings, issues


def render_findings(findings):
    if not findings:
        st.info("This module returned no findings for the current selection.")
    for finding in findings:
        with st.container(border=True):
            st.subheader(finding["title"])
            st.text(finding["description"])
            if finding["denominator"] is not None:
                st.caption(f"Count: {finding['count']} · Denominator: {finding['denominator']} · Percentage: {finding['percentage']}")
            for limit in finding["limitations"]:
                st.caption(limit)


def render_team_page(page, clean_df):
    st.subheader(page)
    if clean_df.empty:
        st.info("No survey rows match these filters. Clear a filter to continue.")
        return
    function, status = load_optional_module(page)
    if status == "missing":
        st.info("Feature in progress. This teammate's module has not been connected yet.")
        return
    if status != "ready":
        st.error(f"This module is present but cannot be used ({status}). Ask its owner to check the import and function contract.")
        return
    try:
        if page == "Action Lab":
            findings, issues = collect_findings(clean_df)
            for issue in issues:
                st.warning(issue)
            if not findings:
                st.info("Action recommendations need validated findings from the analysis modules first.")
                return
            payload = function(findings)
        else:
            payload = function(clean_df.copy(deep=True))
        render_findings(validate_findings(payload))
    except Exception:
        st.error("The module failed or returned an invalid finding structure. No findings are shown; its owner needs to check the module.")


def select_source():
    source = st.sidebar.radio("Data source", ["Synthetic demo", "Upload survey workbook"], key="source_mode")
    if source == "Synthetic demo":
        return demo_result(), "Synthetic demo · not survey evidence", "demo-v1"
    st.sidebar.caption("Use real data only in an approved local or private environment. No workbook is written to disk or placed in the shared cache.")
    workbook = st.sidebar.file_uploader("Survey workbook (.xlsx)", type=["xlsx"], key="survey_upload")
    if workbook is None:
        st.info("Choose your survey Excel workbook in the sidebar, or switch to Synthetic demo.")
        st.stop()
    content = workbook.getvalue()
    token = sha256(content).hexdigest()
    if st.session_state.get("upload_token") != token:
        # Never leave the previous workbook active after an unsuccessful load.
        st.session_state.pop("uploaded_result", None)
        st.session_state.pop("upload_token", None)
        try:
            with st.spinner("Validating the workbook and preparing summaries…"):
                result = run_pipeline(BytesIO(content))
        except Exception:
            st.error("Unable to load this workbook. It must contain the 'Survey Data' sheet and the expected 20 columns. Check it with cleaning.py for a detailed schema or file error.")
            st.stop()
        st.session_state["uploaded_result"] = result
        st.session_state["upload_token"] = token
    return st.session_state["uploaded_result"], "Uploaded survey · private session", token


def sidebar_filters(clean_df, token):
    if st.session_state.get("filter_source") != token:
        for key in ["filter_counties", "filter_roles", "filter_languages", "filter_dates_enabled", "filter_dates"]:
            st.session_state.pop(key, None)
        st.session_state["filter_source"] = token
        st.session_state["loaded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.sidebar.divider()
    st.sidebar.subheader("Explore the survey")
    counties = st.sidebar.multiselect("Training county", sorted(clean_df["county"].dropna().unique()), key="filter_counties")
    roles = st.sidebar.multiselect("Participant role", sorted({r for values in clean_df["role_list"] for r in values}), key="filter_roles")
    languages = st.sidebar.multiselect("Language", sorted(clean_df["language"].dropna().unique()), key="filter_languages")
    st.sidebar.caption("Empty selections include all categories. Selected roles match any chosen role; each row is counted once.")
    dates = clean_df["training_date"].dropna()
    use_dates = st.sidebar.checkbox("Filter by training date", key="filter_dates_enabled", disabled=dates.empty)
    start = end = None
    if use_dates and not dates.empty:
        selected = st.sidebar.date_input("Training date range", value=(dates.min().date(), dates.max().date()),
                                         min_value=dates.min().date(), max_value=dates.max().date(), key="filter_dates")
        if len(selected) != 2:
            st.info("Select both the start and end training dates.")
            st.stop()
        start, end = selected
        st.sidebar.caption("Rows with missing/invalid training dates are excluded by the date filter.")
    min_n = int(st.sidebar.number_input("Minimum paired n for comparisons", min_value=1, max_value=10000, value=20, step=1, key="min_group_n"))
    filtered = filter_survey(clean_df, counties=counties, roles=roles, languages=languages, start_date=start, end_date=end)
    selections = {"counties": counties, "roles": roles, "languages": languages,
                  "start_date": start.isoformat() if start else None,
                  "end_date": end.isoformat() if end else None, "min_group_n": min_n}
    return filtered, selections, min_n


def render_report(clean_df, summary, selections, source_label):
    st.subheader("Report & aggregate export")
    if clean_df.empty:
        st.info("No rows match these filters. Clear a filter before exporting a report.")
        return
    payload = {"data_source": source_label, "selections": selections, **summary}
    st.download_button("Download aggregate summary (JSON)",
                       json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
                       file_name="metrics_summary.json", mime="application/json", key="aggregate_download")
    st.caption("Current selection only. Includes aggregate metrics and limitations; excludes respondent rows, IDs, and comments. Small cells can still be sensitive; public sharing requires appropriate approval.")
    render_pdf_report(clean_df, summary, selections, source_label)

def main():
    st.set_page_config(page_title="Beyond Awareness", page_icon="◉", layout="wide")
    style_app()
    st.sidebar.title("Beyond Awareness")
    st.sidebar.caption("Representation · Measurement · Action")
    page = st.sidebar.radio("Workspace", PAGES, key="workspace_page")
    st.title("Beyond Awareness")
    st.caption("Understanding 988 training · Survey insight workspace")
    result, source_label, token = select_source()
    filtered, selections, min_n = sidebar_filters(result.clean_df, token)
    summary = build_summary(filtered, min_group_n=min_n)
    st.caption(f"{source_label} | {len(filtered):,} of {len(result.clean_df):,} rows selected | Loaded {st.session_state['loaded_at']}")
    if source_label.startswith("Synthetic"):
        st.warning("SYNTHETIC DEMO — Every response shown here is generated for testing. These results are not findings from the real survey.")
    if page == "Overview":
        render_dashboard(filtered, summary)
        render_quality(result.quality)
    elif page == "Report":
        render_report(filtered, summary, selections, source_label)
    elif page == "Gap Detector":
        render_gap_detector(filtered)
    elif page == "Accessibility Audit":
        render_survey_designer(analyze_survey(filtered))
    elif page == "Action Lab":
        render_action_lab(filtered)
    else:
        render_team_page(page, filtered)
    st.divider()
    st.caption("Interpretation: retrospective self-report, not causal evidence. County means training affiliation. Unmeasured barriers must not be presented as observed disparities.")


if __name__ == "__main__":
    main()
