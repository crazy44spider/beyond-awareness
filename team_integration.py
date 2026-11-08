"""Integration adapters for team modules.

Called by Person 1's Streamlit app. The shared cleaned DataFrame remains the
single source for every module. Never print or export raw survey comments.

Person 3's feedback analyzer is intentionally not imported here yet: at the
time of this draft it reads survey_data.xlsx during import, so it cannot
reliably analyze newly uploaded workbooks. Integrate its reusable function
when that is fixed and manually validated.
"""
from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from person2.gap_detector import (
    knowledge_summary,
    knowledge_vs_willingness,
    willingness_summary,
)
from person4.survey_designer import analyze_survey
from intervention_planner import build_action_plan, recommend_interventions
from report_generator import generate_report


def build_action_findings(clean_df: pd.DataFrame) -> list[dict]:
    """Turn Person 2 and safe Person 4 observations into Person 5's schema.

    Not every interesting signal warrants an intervention. In particular,
    Person 4's raw keyword screening is *not* validated qualitative evidence,
    so it remains visible in the Accessibility Audit but is NOT passed along
    as confirmed privacy/language concern.
    """
    if clean_df.empty:
        return []

    audit = analyze_survey(clean_df)
    findings = []

    for item in audit["findings"]:
        kind = item["type"]
        if kind == "call_only_measure":
            converted = dict(item)
            converted["id"] = "communication_measurement_gap"
            converted["type"] = "communication_measurement_gap"
            converted["status"] = "descriptive"
            findings.append(converted)
        elif kind == "low_call_intent_response_rate":
            converted = dict(item)
            converted["status"] = "descriptive"
            findings.append(converted)

    comparison = knowledge_vs_willingness(clean_df)
    n = int(comparison["complete_case_n"])
    count = int(comparison["gap_count"])
    if n > 0 and count > 0:
        findings.append({
            "id": "knowledge_action_gap",
            "source": "gap_detector",
            "type": "knowledge_action_gap",
            "title": "High reported knowledge with lower willingness to call",
            "description": (
                f"{count} of {n} complete cases rated knowing when to use 988 "
                "at 4–5 while reporting call willingness of 0–5."
            ),
            "count": count,
            "denominator": n,
            "percentage": round(count / n * 100, 1),
            "limitations": [
                "Only people answering both questions are included.",
                "Knowledge ratings are retrospective self-reports.",
                "This pattern does not prove why someone would or would not call.",
            ],
            "evidence": {},
            "status": "descriptive",
        })
    return findings


def render_gap_detector(clean_df: pd.DataFrame) -> None:
    """Show Person 2's actual quantitative calculations."""
    st.header("Gap Detector")
    st.caption("Descriptive comparisons: recalled-before versus current ratings, and willingness to call.")
    if clean_df.empty:
        st.info("No survey responses match these filters.")
        return

    knowledge = knowledge_summary(clean_df)
    willingness = willingness_summary(clean_df)
    comparison = knowledge_vs_willingness(clean_df)

    a, b, c = st.columns(3)
    a.metric("Respondents in selection", f"{len(clean_df):,}")
    b.metric("Answered call-intent item", f"{willingness['answered']:,}")
    c.metric("Call-intent response rate", f"{willingness['response_rate']:.1f}%")

    st.subheader("Recalled-before vs current knowledge")
    st.dataframe(
        knowledge[[
            "label", "paired_n", "recalled_before_mean",
            "current_mean", "mean_difference", "percent_increased"
        ]].rename(columns={
            "label": "Knowledge measure",
            "paired_n": "Paired responses",
            "recalled_before_mean": "Recalled-before mean",
            "current_mean": "Current mean",
            "mean_difference": "Mean difference",
            "percent_increased": "Reported increase (%)",
        }),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("All scores are self-reported and retrospective; differences are not causal training effects.")

    st.subheader("Knowledge compared with willingness")
    st.write(
        f"{comparison['complete_case_n']:,} complete cases had both items. "
        f"{comparison['gap_count']:,} rated their knowledge of when to use 988 at 4–5 "
        "while rating willingness to call at 0–5."
    )
    st.caption(
        "Missing willingness answers are excluded. The pattern cannot identify "
        "the reason for lower willingness or measure preference for text/chat."
    )


def render_action_lab(clean_df: pd.DataFrame) -> None:
    """Recommend Person 5's interventions using current, aggregate-only findings."""
    st.header("Action Lab")
    st.caption("Choose possible training improvements informed by the currently selected survey data.")
    if clean_df.empty:
        st.info("No survey responses match these filters.")
        return

    findings = build_action_findings(clean_df)
    result = recommend_interventions(findings)
    recs = result["recommendations"]

    st.subheader("Evidence passed to the planner")
    for finding in findings:
        with st.expander(finding["title"]):
            st.write(finding["description"])
            for note in finding["limitations"]:
                st.caption(note)

    if not recs:
        st.info("No intervention rule matched the current findings.")
        st.session_state["chosen_actions"] = []
        return

    st.subheader("Suggested improvements")
    by_id = {item["id"]: item for item in recs}
    for item in recs:
        with st.expander(item["title"]):
            st.write(item["summary"])
            st.caption(f"Effort: {item.get('effort', 'Not estimated')} (planning estimate only)")
            if item.get("triggered_by"):
                st.write("Triggered by: " + "; ".join(t["title"] for t in item["triggered_by"]))

    prior = [k for k in st.session_state.get("chosen_actions", []) if k in by_id]
    selected = st.multiselect(
        "Select improvements to include in the PDF report",
        options=list(by_id),
        default=prior,
        format_func=lambda key: by_id[key]["title"],
    )
    st.session_state["chosen_actions"] = selected

    if selected:
        st.subheader("Draft action plan")
        for action in build_action_plan(findings, selected):
            with st.expander(action["title"]):
                st.write("**Proposed change:** " + action["proposed_change"])
                st.write("**Future measurement:** " + action["future_measurement"])
                st.write("**Suggested owner:** " + action["owner"])
                st.write("**Decision rule:** " + action["decision_rule"])
    st.caption(
        "Recommendations are candidates for EveryMind review, not proof of effectiveness. "
        "Unvalidated keyword mentions do not automatically trigger actions."
    )


def to_person5_metrics(clean_df: pd.DataFrame, summary: dict, source_label: str) -> dict:
    """Translate Person 1's aggregate summary into Person 5's PDF schema."""
    overview = summary.get("overview", {})
    n = int(overview.get("survey_rows", len(clean_df)))
    topics = summary.get("knowledge", {}).get("topics", {})
    knowledge_rows = [
        {
            "measure": topic,
            "before_mean": stats.get("before_mean"),
            "current_mean": stats.get("after_mean"),
            "n_paired": stats.get("n"),
        }
        for topic, stats in topics.items()
    ]

    dates = clean_df["training_date"].dropna() if "training_date" in clean_df else pd.Series(dtype="datetime64[ns]")
    period = "Not available"
    if not dates.empty:
        period = f"{dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d}"

    return {
        "status": "synthetic" if source_label.startswith("Synthetic") else "real",
        "dataset_period": period,
        "n_responses": n,
        "responses_verified": not source_label.startswith("Synthetic"),
        "scale_note": "Recalled-before and current knowledge on the 1–5 response scale.",
        "scale_max": 5,
        "knowledge": knowledge_rows,
        "call_intent": {
            "n_answered": int(overview.get("willingness_valid_n", 0)),
            "n_total": n,
        },
        # No qualitative themes are claimed validated until Person 3
        # supplies an import-safe analyzer and manual classification checks.
        "themes": [],
        "approved_excerpts": [],
        "dimension_status": {
            "Cultural and social norms": "Unmeasured",
            "Practical / socioeconomic": "Unmeasured",
            "Communication access": "Indirectly mentioned",
            "Institutional trust": "Unmeasured",
            "Psychological comfort": "Unmeasured",
        },
    }


def render_pdf_report(clean_df: pd.DataFrame, summary: dict, selections: dict, source_label: str) -> None:
    """Generate Person 5's real PDF with the correct argument names."""
    st.subheader("Improvement Brief (PDF)")
    if clean_df.empty:
        st.info("No responses selected.")
        return

    chosen = st.session_state.get("chosen_actions", [])
    st.write(f"Actions chosen in Action Lab: **{len(chosen)}**")
    if not chosen:
        st.caption("You can generate a report now, or visit Action Lab and select improvements first.")

    findings = build_action_findings(clean_df)
    metrics = to_person5_metrics(clean_df, summary, source_label)
    signature = hashlib.sha256(
        json.dumps(
            {"metrics": metrics, "findings": findings, "selected": chosen, "filters": selections},
            sort_keys=True, default=str,
        ).encode("utf-8")
    ).hexdigest()

    if st.session_state.get("generated_pdf_signature") != signature:
        st.session_state.pop("generated_pdf_bytes", None)
        st.session_state["generated_pdf_signature"] = signature

    if st.button("Generate Improvement Brief", key="integrated_pdf_generate"):
        try:
            pdf = generate_report(
                metrics=metrics,
                findings=findings,
                selected_interventions=chosen,
            )
            if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-"):
                raise ValueError("PDF generator returned an invalid file.")
            st.session_state["generated_pdf_bytes"] = pdf
        except Exception:
            st.error("PDF generation failed. Check the report generator and dependency installation.")

    if st.session_state.get("generated_pdf_bytes"):
        st.download_button(
            "Download Improvement Brief (PDF)",
            data=st.session_state["generated_pdf_bytes"],
            file_name="everymind_improvement_brief.pdf",
            mime="application/pdf",
            key="integrated_pdf_download",
        )
    st.caption("The PDF includes aggregate data only; it does not export respondent-level comments.")
