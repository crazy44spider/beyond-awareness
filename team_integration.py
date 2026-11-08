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
from person4.survey_designer import analyze_survey, coverage_audit
from intervention_planner import (
    DIMENSION_NAMES, build_action_plan, get_dimension_info,
    get_intervention, recommend_interventions,
)
from ui_styles import intro, stat_cards, focus_card
from report_generator import generate_report
from feedback_analyzer import analyze_feedback


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
    """Plain-English first; all original stats remain under 'Detailed evidence'."""
    intro(
        "WHAT PEOPLE KNOW · WHAT WE CAN MEASURE",
        "Understanding is only part of the story",
        "Explore what people reported learning, and where we're still missing answers.",
    )
    if clean_df.empty:
        st.info("No survey responses match these filters.")
        return

    knowledge = knowledge_summary(clean_df)
    willingness = willingness_summary(clean_df)
    comparison = knowledge_vs_willingness(clean_df)
    answered = willingness["answered"]
    rate = willingness["response_rate"]

    stat_cards([
        {
            "tone": "lilac", "icon": "💜",
            "label": "Responses included",
            "value": f"{len(clean_df):,}",
            "detail": "Current filters",
        },
        {
            "tone": "mint", "icon": "📚",
            "label": "Answered the call question",
            "value": f"{answered:,}",
            "detail": "Missing does not mean unwilling",
        },
        {
            "tone": "peach", "icon": "💬",
            "label": "Call question response rate",
            "value": f"{rate:.1f}%" if pd.notna(rate) else "N/A",
            "detail": "Only the calling route was asked about",
        },
    ])

    st.write("")
    st.subheader("Where participants report learning")
    st.caption(
        "The share whose current rating was higher than their recalled-before rating."
    )
    for _, item in knowledge.iterrows():
        label = str(item["label"])
        paired = int(item["paired_n"])
        value = item["percent_increased"]
        if paired == 0 or pd.isna(value):
            st.write(f"**{label}** · No matched answers")
            continue
        pct = max(0.0, min(100.0, float(value)))
        col_label, col_pct = st.columns([4, 1])
        with col_label:
            st.markdown(f"**{label}**")
        with col_pct:
            st.markdown(f"**{pct:.0f}%**")
        st.progress(pct / 100)
        st.caption(f"Among {paired:,} paired survey responses")

    n = int(comparison["complete_case_n"])
    if n:
        count = int(comparison["gap_count"])
        focus_card(
            "AN AWARENESS–ACTION QUESTION",
            "Some people know when to use 988, but rate calling lower",
            f"{count} of {n} people who answered both items rated their knowledge "
            "of when to use 988 at 4–5 but willingness to call at 0–5. "
            "This is a descriptive pattern, not an explanation of why.",
        )
    else:
        st.info("Not enough paired knowledge and willingness answers for a comparison.")

    with st.expander("Detailed evidence · scores, counts, correlation and methodology"):
        st.subheader("Matched knowledge comparisons")
        st.dataframe(
            knowledge[[
                "label", "paired_n", "recalled_before_mean",
                "current_mean", "mean_difference", "percent_increased",
            ]].rename(columns={
                "label": "Knowledge measure",
                "paired_n": "Paired responses",
                "recalled_before_mean": "Recalled-before mean",
                "current_mean": "Current mean",
                "mean_difference": "Mean difference",
                "percent_increased": "Reported increase (%)",
            }),
            hide_index=True,
            width="stretch",
        )
        st.subheader("Knowledge and willingness")
        st.write(
            f"{n:,} complete cases; {comparison['gap_count']:,} matched the "
            "high-knowledge/lower-willingness definition."
        )
        st.markdown("**Cross-tabulation (knowledge 1–5 × willingness 0–10)**")
        st.dataframe(comparison["heatmap"], width="stretch")
        st.markdown("**Call-intent distribution (0–10)**")
        st.dataframe(
            pd.DataFrame(
                list(willingness["score_distribution"].items()),
                columns=["Willingness score", "Count"],
            ),
            hide_index=True,
            width="stretch",
        )
        corr = comparison["spearman_correlation"]
        if pd.notna(corr):
            st.caption(f"Spearman correlation: {float(corr):.2f} (descriptive, complete cases only).")
        st.caption(
            "Recalled-before scores were collected after training. Scores are ordinal "
            "self-reports; gaps and correlations are not causal effects. Missing "
            "call-intent answers may be nonrandom, and this survey does not ask "
            "whether people prefer text or chat."
        )


def render_action_lab(clean_df: pd.DataFrame) -> None:
    """Preserve the planner while exposing its richer comparison/lens tools."""
    intro(
        "FROM FINDINGS TO THE NEXT TRAINING",
        "Small changes, meaningful next steps",
        "Explore candidate improvements, compare options, and build a practical action plan.",
    )
    if clean_df.empty:
        st.info("No survey responses match these filters.")
        return

    findings = build_action_findings(clean_df)
    result = recommend_interventions(findings)
    recs = result["recommendations"]
    by_id = {item["id"]: item for item in recs}

    stat_cards([
        {
            "tone": "lilac", "icon": "💡", "label": "Evidence signals",
            "value": str(len(findings)), "detail": "Descriptive, not causal",
        },
        {
            "tone": "mint", "icon": "🌱", "label": "Suggested improvements",
            "value": str(len(recs)), "detail": "Ideas for EveryMind review",
        },
    ])

    tab1, tab2, tab3, tab4 = st.tabs([
        "Explore improvements", "Compare actions",
        "Inclusive action lens", "Your action plan",
    ])

    with tab1:
        st.subheader("Recommended changes")
        st.caption(
            "These proposals depend on the current survey selection. "
            "Effort levels are planning estimates, not predicted outcomes."
        )
        if not recs:
            st.info("No matching recommendations for this selection.")
            st.session_state["chosen_actions"] = []
        else:
            for item in recs:
                with st.expander("✨  " + item["title"]):
                    st.write(item["summary"])
                    st.markdown(f"**Why:** {item['why']}")
                    st.caption(f"Effort: {item.get('effort', 'Not estimated')}")
                    if item.get("triggered_by"):
                        st.write(
                            "Evidence: " + "; ".join(
                                t["title"] for t in item["triggered_by"]
                            )
                        )
                    st.markdown("**How to try it**")
                    for step in item["steps"]:
                        st.write("- " + step)
                    st.write("**Measure:** " + item["metric"])
            prior = [
                item for item in st.session_state.get("chosen_actions", [])
                if item in by_id
            ]
            selected = st.multiselect(
                "Add improvements to your action plan",
                options=list(by_id),
                default=prior,
                format_func=lambda key: by_id[key]["title"],
            )
            st.session_state["chosen_actions"] = selected

        with st.expander("What evidence triggered these suggestions?"):
            for finding in findings:
                st.markdown("**" + finding["title"] + "**")
                st.write(finding["description"])
                for note in finding["limitations"]:
                    st.caption(note)
            if not findings:
                st.caption("No findings available for this selection.")

    with tab2:
        st.subheader("Compare your options")
        st.caption(
            "Compare up to three recommended actions. 'Effort' is an estimate, not a score of likely success."
        )
        if not recs:
            st.info("Recommendations will appear here when the current selection produces findings.")
        else:
            compare = st.multiselect(
                "Compare actions (up to three)",
                options=list(by_id),
                default=list(by_id)[:2],
                format_func=lambda key: by_id[key]["title"],
                key="compare_action_ids",
            )
            if len(compare) > 3:
                st.warning("Showing the first three selections.")
                compare = compare[:3]
            if compare:
                fields = [
                    ("Intended outcome", "outcome"),
                    ("Implementation steps", "steps"),
                    ("Estimated effort", "effort"),
                    ("How to measure", "metric"),
                    ("What could change this choice", "change_mind"),
                ]
                table = {}
                for key in compare:
                    item = by_id[key]
                    table[item["title"]] = [
                        "\n".join(item.get(field, []))
                        if isinstance(item.get(field), list)
                        else str(item.get(field, "Not available"))
                        for _, field in fields
                    ]
                st.table(
                    pd.DataFrame(
                        table,
                        index=[name for name, _ in fields],
                    )
                )

    with tab3:
        st.subheader("Inclusive action lens")
        st.caption(
            "Consider unmeasured barriers without assuming they exist in any particular community."
        )
        dimension = st.selectbox(
            "Which dimension would you like to consider?",
            DIMENSION_NAMES,
            key="integrated_inclusive_dimension",
        )
        info = get_dimension_info(dimension)
        if info:
            st.markdown("**What this survey actually establishes**")
            st.write(info["established"])
            st.markdown("**What we don't yet know**")
            st.write(info["unknown"])
            with st.expander("Ideas to try and how to measure them", expanded=True):
                st.markdown("**Possible design changes**")
                for idea in info["design_choices"]:
                    st.write("- " + idea)
                st.markdown("**Optional questions for future surveys**")
                for question in info["future_questions"]:
                    st.write("- " + question)
                st.caption(info["interpretation"])

    with tab4:
        st.subheader("Your draft action plan")
        selected = st.session_state.get("chosen_actions", [])
        if not selected:
            st.info("Choose at least one improvement on the first tab to build a plan.")
        else:
            for action in build_action_plan(findings, selected):
                with st.expander(action["title"], expanded=True):
                    st.write("**Proposed change:** " + action["proposed_change"])
                    st.write("**Suggested owner:** " + action["owner"])
                    st.write("**Future measurement:** " + action["future_measurement"])
                    st.write("**Decision rule:** " + action["decision_rule"])
                    st.write("**Check-in:** " + action["checkin"])
                    st.markdown("**Implementation steps**")
                    for step in action["steps"]:
                        st.write("- " + step)
            st.success("Your selected actions can be exported from the Reports page.")

    st.caption(
        "Suggested actions are hypotheses to test and refine with EveryMind, "
        "not evidence of proven impact. Unvalidated comment keyword matches "
        "are not presented as confirmed participant concerns."
    )


@st.cache_data(show_spinner=False, ttl=3600, max_entries=6)
def _pdf_feedback_counts(voice_df: pd.DataFrame) -> tuple[pd.Series, int]:
    """Cache the same keyword coding used by Participant Voices."""
    result = analyze_feedback(voice_df)
    skip = {
        "Other", "Too brief to code",
        "Positive / nothing to change",
        "No further questions / nothing to add",
        "Answered about helping others / self (not the training)",
    }
    counts = result["improve_counts"]
    counts = counts[~counts.index.isin(skip)].head(5)
    valid_comments = int(result["data"]["improve_en"].notna().sum())
    return counts, valid_comments


def to_person5_metrics(clean_df: pd.DataFrame, summary: dict, source_label: str) -> dict:
    """Use current filtered data for PDF figures, not hardcoded audit statuses."""
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

    dates = (
        clean_df["training_date"].dropna()
        if "training_date" in clean_df else pd.Series(dtype="datetime64[ns]")
    )
    period = "Not available"
    if not dates.empty:
        period = f"{dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d}"

    relation = knowledge_vs_willingness(clean_df) if not clean_df.empty else {}
    paired = int(relation.get("complete_case_n", 0))
    gap_n = int(relation.get("gap_count", 0))
    relation_summary = (
        f"{gap_n} of {paired} paired answers ({100*gap_n/paired:.1f}%) "
        "reported knowing when to use 988 at 4–5 of 5 but willingness "
        "to call at 0–5 of 10. The survey does not establish why."
        if paired else
        "No paired knowledge-and-willingness answers were available."
    )

    # Question columns are retained in the cleaned frame. A revised upload
    # must therefore change both the Survey Designer AND the PDF audit.
    design = coverage_audit(clean_df)
    audit_map = {
        "Cultural & Linguistic": "Cultural and social norms",
        "Socioeconomic & Practical": "Practical / socioeconomic",
        "Communication": "Communication access",
        "Institutional Trust": "Institutional trust",
        "Psychological": "Psychological comfort",
    }
    statuses = {
        "Directly measured": "Measured (added question)",
        "Partially measured": "Partially measured",
        "Not directly measured": "Unmeasured",
    }
    dimension_status = {
        audit_map[row["dimension"]]: statuses.get(row["coverage"], "Unmeasured")
        for _, row in design.iterrows()
        if row["dimension"] in audit_map
    }

    # Counts are preliminary keyword matches, not validated interpretations.
    # No individual comments or raw participant IDs enter PDF metrics.
    themes = []
    if not clean_df.empty:
        preview_columns = [
            col for col in (
                "id", "valuable_feedback", "improvement_feedback",
                "county", "participant_type",
            ) if col in clean_df
        ]
        counts, usable = _pdf_feedback_counts(clean_df[preview_columns].copy())
        themes = [
            {"theme": str(label), "count": int(value),
             "denominator": usable, "validated": False}
            for label, value in counts.items()
        ]

    return {
        "status": "synthetic" if source_label.startswith("Synthetic") else "real",
        "dataset_period": period,
        "n_responses": n,
        "responses_verified": False,
        "scale_note": "Recalled-before and current knowledge on the 1–5 response scale.",
        "scale_max": 5,
        "knowledge": knowledge_rows,
        "call_intent": {
            "n_answered": int(overview.get("willingness_valid_n", 0)),
            "n_total": n,
        },
        "knowledge_call_relationship": {
            "n": paired,
            "summary": relation_summary,
        },
        "themes": themes,
        "approved_excerpts": [],
        "dimension_status": dimension_status,
    }


def render_pdf_report(clean_df: pd.DataFrame, summary: dict, selections: dict, source_label: str) -> None:
    """Generate Person 5's real PDF with the correct argument names."""
    st.subheader("Improvement Brief (PDF)")
    if clean_df.empty:
        st.info("No responses selected.")
        return

    chosen = st.session_state.get("chosen_actions", [])
    st.write(f"Actions selected in Intervention Planner: **{len(chosen)}**")
    if not chosen:
        st.caption("You can generate a findings-only report now. To include an action plan, select improvements in Intervention Planner.")

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
