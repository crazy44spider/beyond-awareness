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
from pathlib import Path
import random

import pandas as pd
import streamlit as st

from cleaning import EXPECTED_COLUMNS, KNOWLEDGE_COLUMNS, clean_survey, summarize_quality
from pipeline import PipelineResult, build_summary, filter_survey, run_pipeline
from dashboard import render_dashboard, render_quality, style_app
from person4.survey_designer import analyze_survey, render_survey_designer
from team_integration import render_gap_detector, render_action_lab, render_pdf_report
from feedback_analyzer import analyze_feedback
from story_theme import apply_theme
from story_pages import (
    render_overview, render_training_outcomes, render_gap_diagnostic,
    render_participant_voices as render_story_voices, render_survey_workspace,
    render_intervention_roadmap, render_reports, render_detailed_analysis,
)

PAGES = [
    "Overview",
    "Training Outcomes",
    "Gap Detector",
    "Participant Voices",
    "Survey Designer",
    "Intervention Planner",
    "Reports",
    "Detailed Analysis",
]
NAV_LABELS = {
    "Overview": "Overview",
    "Training Outcomes": "Training Outcomes",
    "Gap Detector": "Gap Detector",
    "Participant Voices": "Participant Voices",
    "Survey Designer": "Survey Designer",
    "Intervention Planner": "Intervention Planner",
    "Reports": "Reports",
    "Detailed Analysis": "Detailed Analysis",
}

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
            valuable_feedback=[
                "I learned when to call 988",
                "988 is available 24/7",
                "Anyone can use the support line",
                "How to help a friend in need",
            ][i % 4],
            improvement_feedback=[
                "Please include more interactive activities",
                "I would like more examples and practice",
                "Can you explain confidentiality?",
                "More videos and visual examples would help",
            ][i % 4],
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



def render_participant_voices(clean_df):
    """Explore aggregate themes from the currently filtered workbook."""
    st.header("What participants said")
    st.caption("Explore what people valued and what they would change.")
    if clean_df.empty:
        st.info("No survey responses match the current filters.")
        return

    try:
        analysis = analyze_feedback(clean_df)
    except Exception:
        st.error("Could not analyze feedback for this survey. Check its columns.")
        return

    tab = st.radio(
        "Explore",
        ["What people valued", "What people would improve"],
        horizontal=True,
        key="voice_category",
    )
    is_improve = tab == "What people would improve"
    counts = analysis["improve_counts" if is_improve else "learned_counts"]
    tag_col = "improve_themes" if is_improve else "learned_themes"
    comments = "improve_en" if is_improve else "learned_en"
    tagged = analysis["data"]
    n = int(tagged[comments].notna().sum())
    st.caption(f"{n:,} responses with comments · A comment may match multiple themes.")

    if counts.empty:
        st.info("No coded comments in this selection.")
        return
    counts = counts.head(12)
    st.subheader("Most common themes")
    st.bar_chart(counts.rename("Theme matches"), horizontal=True, height=330)
    theme = st.selectbox("Explore a theme", counts.index.tolist())
    matching = tagged[tagged[tag_col].apply(lambda tags: theme in tags)]
    st.write(f"**{len(matching):,}** matching comments")
    st.caption(
        "Theme matches use keyword rules and may contain false positives. "
        "Review examples privately before sharing them."
    )
    if st.checkbox(
        "Show redacted comment examples (private review only)",
        value=False,
        key="private_comment_examples",
    ):
        st.warning(
            "Automated name redaction is incomplete. Do not screenshot, "
            "publish, or export these comments without a privacy review."
        )
        for value in matching[comments].dropna().head(5):
            st.write(str(value))

def select_source():
    """Use the local real workbook when available; otherwise ask for an upload.

    Synthetic examples are an explicit testing choice, never the default.
    Keep real rows private to this local Streamlit session.
    """
    local_workbook = Path(__file__).resolve().parent / "survey_data.xlsx"
    with st.sidebar.expander("Data source", expanded=False):
        mode = st.radio(
            "Use",
            ["Real survey", "Synthetic test data"],
            key="source_mode_v2",
            label_visibility="collapsed",
        )
        if mode == "Real survey":
            uploaded = st.file_uploader(
                "Replace with a survey workbook",
                type=["xlsx"],
                key="survey_upload",
                help="Use a private/local environment for participant data.",
            )
        else:
            uploaded = None

    if mode == "Synthetic test data":
        return demo_result(), "Synthetic test data", "demo-v1"

    if uploaded is not None:
        content = uploaded.getvalue()
        token = "uploaded-" + sha256(content).hexdigest()
        source = BytesIO(content)
        label = "Uploaded survey"
    elif local_workbook.is_file():
        # Local-only convenience: don't commit the workbook to GitHub.
        # Fingerprint metadata to refresh when the workbook is replaced.
        stat = local_workbook.stat()
        token = f"local-{stat.st_size}-{stat.st_mtime_ns}"
        source = local_workbook
        label = "EveryMind survey"
    else:
        st.info(
            "To see the real survey, put survey_data.xlsx beside app.py, "
            "or upload the Excel workbook in the Data source section of the sidebar."
        )
        st.stop()

    if st.session_state.get("upload_token") != token:
        st.session_state.pop("uploaded_result", None)
        st.session_state.pop("upload_token", None)
        try:
            with st.spinner("Loading survey responses…"):
                result = run_pipeline(source)
        except Exception:
            st.error(
                "Could not read the survey workbook. Check that it contains "
                "the 'Survey Data' worksheet and the expected columns."
            )
            st.stop()
        st.session_state["uploaded_result"] = result
        st.session_state["upload_token"] = token

    return st.session_state["uploaded_result"], label, token


def sidebar_filters(clean_df, token):
    """Keep all filters, but tuck them into one optional sidebar drawer."""
    if st.session_state.get("filter_source") != token:
        for key in [
            "filter_counties", "filter_roles", "filter_languages",
            "filter_dates_enabled", "filter_dates",
        ]:
            st.session_state.pop(key, None)
        # Don't reuse actions or an exported report from the previous workbook.
        for key in ["chosen_actions", "generated_pdf_bytes", "generated_pdf_signature",
                    "story_extra_actions", "story_survey_selected", "story_filters_token"]:
            st.session_state.pop(key, None)
        for key in list(st.session_state.keys()):
            if key.startswith(("story_action_", "voice_theme_", "private_voice_")):
                st.session_state.pop(key, None)
        st.session_state["filter_source"] = token
        st.session_state["loaded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with st.sidebar.expander("🔎  Filter responses", expanded=False):
        st.caption("Filters apply to every page.")
        counties = st.multiselect(
            "Training county",
            sorted(clean_df["county"].dropna().unique()),
            key="filter_counties",
        )
        roles = st.multiselect(
            "Participant role",
            sorted({r for values in clean_df["role_list"] for r in values}),
            key="filter_roles",
        )
        languages = st.multiselect(
            "Language",
            sorted(clean_df["language"].dropna().unique()),
            key="filter_languages",
        )
        dates = clean_df["training_date"].dropna()
        use_dates = st.checkbox(
            "Filter by training date", key="filter_dates_enabled", disabled=dates.empty
        )
        start = end = None
        if use_dates and not dates.empty:
            selected = st.date_input(
                "Training date range",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
                key="filter_dates",
            )
            if len(selected) != 2:
                st.info("Select both the start and end dates.")
                st.stop()
            start, end = selected

        
        
        min_n = int(
            st.number_input(
                "Minimum paired responses",
                min_value=1,
                max_value=10000,
                value=20,
                step=1,
                key="min_group_n",
                help="Groups with fewer paired answers than this are not compared.",
            )
        )

    filtered = filter_survey(
        clean_df,
        counties=counties,
        roles=roles,
        languages=languages,
        start_date=start,
        end_date=end,
    )
    selections = {
        "counties": counties,
        "roles": roles,
        "languages": languages,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "min_group_n": min_n,
    }
    st.sidebar.caption(f"Viewing **{len(filtered):,}** of {len(clean_df):,} survey rows")
    return filtered, selections, min_n


def render_report(clean_df, summary, selections, source_label):
    st.header("Your Improvement Brief")
    st.caption(
        "Turn the selected findings and actions into a shareable, aggregate-only PDF."
    )
    if clean_df.empty:
        st.info("No rows match these filters. Clear a filter before exporting a report.")
        return

    # Keep the original JSON export, but make it an advanced option.
    payload = {"data_source": source_label, "selections": selections, **summary}
    render_pdf_report(clean_df, summary, selections, source_label)

    with st.expander("Advanced export · aggregate summary (JSON)"):
        st.download_button(
            "Download aggregate JSON",
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
            file_name="metrics_summary.json",
            mime="application/json",
            key="aggregate_download",
        )
        st.caption(
            "Current selection only. Includes aggregate metrics and limitations, "
            "not respondent rows, IDs, or comments. Small cells can still be sensitive; "
            "public sharing requires approval."
        )



def main():
    st.set_page_config(
        page_title="Beyond Awareness | EveryMind",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # The original style layer remains intact for legacy views.
    style_app()
    apply_theme()

    st.sidebar.markdown(
        '<div style="margin:6px 0 18px">'
        '<div style="display:inline-block;border:1px solid #8DBB9B;'
        'border-radius:9px;padding:7px 9px;color:#F4F7EF;'
        'font-size:.8rem;font-weight:800;letter-spacing:.10em">B/A</div>'
        '<div style="font-family:Georgia,serif;color:#FFFDF7;font-size:1.6rem;'
        'line-height:1.1;margin-top:12px">Beyond<br>Awareness</div>'
        '<div style="color:#B9D4C0;font-size:.76rem;margin-top:7px">'
        'EveryMind · 988 training</div></div>',
        unsafe_allow_html=True,
    )

    result, source_label, token = select_source()
    filtered, selections, min_n = sidebar_filters(result.clean_df, token)

    st.sidebar.divider()
    st.sidebar.caption("EXPLORE")
    if st.session_state.get("workspace_page") not in PAGES:
        st.session_state["workspace_page"] = "Overview"
    page = st.sidebar.radio(
        "Pages",
        PAGES,
        format_func=lambda item: NAV_LABELS[item],
        label_visibility="collapsed",
        key="workspace_page",
    )

    # Re-selecting a subset must not carry a previously generated PDF or action
    # selection into a different evidence base.
    current_filter_token = json.dumps(
        {"source": token, "selections": selections},
        sort_keys=True, default=str,
    )
    if st.session_state.get("story_filters_token") != current_filter_token:
        for name in ("chosen_actions", "generated_pdf_bytes", "generated_pdf_signature",
                     "story_extra_actions", "story_survey_selected"):
            st.session_state.pop(name, None)
        for name in list(st.session_state.keys()):
            if name.startswith(("story_action_", "voice_theme_", "private_voice_")):
                st.session_state.pop(name, None)
        st.session_state["story_filters_token"] = current_filter_token

    summary = build_summary(filtered, min_group_n=min_n)

    st.caption(f"{source_label}  ·  {len(filtered):,} responses selected")
    if source_label.startswith("Synthetic"):
        st.warning("TEST DATA — this is not EveryMind survey evidence.")

    if page == "Overview":
        render_overview(filtered, summary, source_label)
    elif page == "Training Outcomes":
        render_training_outcomes(filtered, summary)
    elif page == "Gap Detector":
        render_gap_diagnostic(filtered)
    elif page == "Participant Voices":
        render_story_voices(filtered)
    elif page == "Survey Designer":
        render_survey_workspace(filtered)
    elif page == "Intervention Planner":
        render_intervention_roadmap(filtered)
    elif page == "Reports":
        render_reports(filtered, summary, selections, source_label)
    elif page == "Detailed Analysis":
        render_detailed_analysis(filtered, summary, result.quality)

    st.markdown(
        '<p style="font-size:.72rem;color:#728477;margin:34px 0 4px">'
        'Beyond Awareness · Retrospective participant self-report. '
        'Patterns are descriptive, not proof of cause or access barriers.</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
