"""Story-first Streamlit pages for Beyond Awareness.

This module ONLY changes presentation and routing. It calls the existing
analysis, cleaning, survey designer, intervention planner, and report generator.
No fabricated values, no new respondent-level exports.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from dashboard import (
    render_comparisons,
    render_experience,
    render_knowledge,
    render_missingness,
    render_quality,
    render_representation,
    render_overview as render_original_overview,
)
from feedback_analyzer import analyze_feedback
from voice_explorer import make_voice_explorer_html
from intervention_planner import (
    build_action_plan,
    get_intervention,
    list_interventions,
    recommend_interventions,
)
from person2.gap_detector import knowledge_summary, knowledge_vs_willingness, willingness_summary
from person4.survey_designer import (
    analyze_survey,
    export_selected_questions,
    question_bank,
)
from story_theme import (
    BARK, FOREST, GOLD, GRID, INK, JADE, MUTED, SAGE,
    esc, flow_step, guide_card, heading, kpis, pill, takeaway,
)
from team_integration import (
    build_action_findings,
    render_action_lab as render_original_action_lab,
    render_pdf_report,
)


def _navigate(page: str) -> None:
    st.session_state["workspace_page"] = page


def _pct(frac: Any) -> str:
    if frac is None or pd.isna(frac):
        return "Unavailable"
    return f"{float(frac)*100:.0f}%"


def _short_num(value: Any, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "Unavailable"
    return f"{float(value):.{digits}f}"


def _lock_figure(fig: go.Figure) -> go.Figure:
    """Keep hover readouts; prevent zoom, pan, axis editing and legend hiding.

    Plotly's hidden modebar alone does not lock navigation, and a legend
    click can otherwise make an entire dataset appear to disappear.
    """
    fig.update_layout(
        dragmode=False,
        clickmode="none",
        legend=dict(itemclick=False, itemdoubleclick=False),
    )
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


PLOT_CONFIG = {
    "displaylogo": False,
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "editable": False,
    "showAxisDragHandles": False,
    "showAxisRangeEntryBoxes": False,
    "responsive": True,
}


def _plot(fig: go.Figure, key: str, *, height: int = 320, left: int = 60) -> None:
    """A full-width, non-editable chart with readable axes and useful tooltips."""
    visible_legend = (
        bool(fig.layout.showlegend) if fig.layout.showlegend is not None
        else (
            any(trace.showlegend is True for trace in fig.data)
            or sum(bool(trace.name) and trace.showlegend is not False
                   for trace in fig.data) > 1
        )
    )
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Arial, sans-serif", size=13, color=INK),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=[JADE, BARK, "#91B59A", "#D5BA96"],
        margin=dict(l=left, r=30, t=63 if visible_legend else 28, b=54),
        height=height,
        showlegend=visible_legend,
        legend=dict(
            orientation="h", y=1.16, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=12),
        ),
        hovermode="closest",
        hoverlabel=dict(bgcolor="#F7F8F2", font=dict(color=INK, size=12)),
        bargap=.25,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, automargin=True)
    _lock_figure(fig)
    st.plotly_chart(fig, key=key, width="stretch", theme=None, config=PLOT_CONFIG)


def render_overview(clean_df: pd.DataFrame, summary: dict, source_label: str) -> None:
    """A true entry point: outcome, blind spot, and what to explore next."""
    overview = summary["overview"]
    n = int(overview["survey_rows"])
    answered = int(overview["willingness_valid_n"])
    rate = overview["willingness_response_rate"]
    missing = int(overview["willingness_missing_or_invalid_n"])

    heading(
        "BEYOND AWARENESS / 988 TRAINING",
        "Training matters. So does what comes after.",
        "A practical view of what participants learned, what remains unknown, "
        "and where EveryMind can improve its next training.",
        dark=True,
    )

    kpis([
        ("Responses included", f"{n:,}", "Current survey selection"),
        ("Answered the willingness-to-call question", _pct(rate), f"{answered:,} of {n:,} responded; {missing:,} missing or invalid"),
    ])

    knowledge = summary["knowledge"]["topics"]
    higher = [
        label for label, stats in knowledge.items()
        if stats["n"] and stats["mean_change"] is not None and stats["mean_change"] > 0
    ]
    measured = sum(1 for stats in knowledge.values() if stats["n"])
    if measured and len(higher) == measured:
        headline = "All measured topics had higher current self-ratings."
    elif higher:
        headline = "Some knowledge topics had higher current self-ratings."
    elif measured:
        headline = "No measured topic showed a higher average self-rating."
    else:
        headline = "Paired knowledge ratings are unavailable."
    takeaway(
        headline,
        "These are retrospective participant ratings, not proof "
        "that the training caused a change.",
        label="WHAT THE SURVEY SUGGESTS",
    )

    st.markdown("### Explore the story")
    st.caption("Each section answers a different question.")
    left, middle, right = st.columns(3, gap="medium")
    with left:
        guide_card("01 / OUTCOMES", "What did they learn?", "See the three knowledge areas side by side.")
        st.button(
            "Explore learning",
            use_container_width=True,
            on_click=_navigate,
            args=("Training Outcomes",),
            key="jump_outcomes",
        )
    with middle:
        guide_card("02 / PARTICIPANTS", "What did they say?", "Explore themes from the written feedback.")
        st.button(
            "Read participant voices",
            use_container_width=True,
            on_click=_navigate,
            args=("Participant Voices",),
            key="jump_voices",
        )
    with right:
        guide_card("03 / ACTION", "What should change?", "Build an improvement plan based on findings.")
        st.button(
            "Plan improvements",
            use_container_width=True,
            on_click=_navigate,
            args=("Intervention Planner",),
            key="jump_actions",
        )

    st.caption(
        "The survey records answers from respondents, not verified unique people. "
        "All results on this page follow the selected filters."
    )


def render_training_outcomes(clean_df: pd.DataFrame, summary: dict) -> None:
    """A single large dumbbell chart. Detailed distribution analyses stay elsewhere."""
    heading(
        "01 / TRAINING OUTCOMES",
        "What did participants learn?",
        "Three skills. One comparison.",
    )
    records = summary["knowledge"]["topics"]
    usable = [(label, item) for label, item in records.items()
              if item["n"] and item["before_mean"] is not None and item["after_mean"] is not None]
    if not usable:
        st.info("No matched before-and-after knowledge ratings for the current filters.")
        return

    translated = {
        "Identify crisis": "Recognize a crisis",
        "Describe 988": "Explain 988",
        "Know when to use 988": "Know when to use 988",
    }
    fig = go.Figure()
    for index, (name, row) in enumerate(usable):
        y = translated.get(name, name)
        before = float(row["before_mean"])
        after = float(row["after_mean"])
        fig.add_trace(go.Scatter(
            x=[before, after], y=[y, y], mode="lines",
            line=dict(color="#D3C2AB", width=8), showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[before], y=[y], mode="markers",
            marker=dict(color=BARK, size=15, line=dict(color="white", width=2)),
            showlegend=index == 0, name="Recalled before",
            hovertemplate="%{y}: %{x:.2f}<extra>Recalled before</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[after], y=[y], mode="markers",
            marker=dict(color=JADE, size=17, line=dict(color="white", width=2)),
            showlegend=index == 0, name="Current",
            hovertemplate="%{y}: %{x:.2f}<extra>Current</extra>",
        ))
    st.subheader("Recalled-before vs. current knowledge ratings")
    fig.update_xaxes(range=[.8, 5.2], title="Agreement score, 1–5", dtick=1)
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=[translated.get(name, name) for name, _ in usable][::-1],
        showgrid=False,
        tickfont=dict(size=12),
        automargin=True,
    )
    _plot(fig, "story_learning_dumbbell", height=330, left=185)

    improved = [
        (label, item) for label, item in usable
        if float(item["after_mean"]) > float(item["before_mean"])
    ]
    if improved:
        strongest_name, strongest = max(
            improved, key=lambda pair: float(pair[1]["mean_change"])
        )
        largest = translated.get(strongest_name, strongest_name).lower()
        takeaway(
            f"Largest reported difference: {largest} "
            f"(+{float(strongest['mean_change']):.2f} points).",
            f"Based on {int(strongest['n']):,} paired responses on the 1–5 agreement scale. "
            "These are recalled-before versus current self-ratings, not causal proof.",
            label="KEY FINDING",
        )
    else:
        takeaway(
            "No knowledge topic has a higher current average.",
            "Only matched before/current ratings are compared. "
            "A reported difference cannot establish a causal effect.",
            label="KEY FINDING",
        )

    st.caption(
        "Participants reported what they remembered knowing before the training only afterward. "
        "These comparisons describe perceptions, not causal effects."
    )
    st.button(
        "See distributions and group comparisons in Data Explorer",
        key="outcomes_to_details",
        on_click=_navigate,
        args=("Detailed Analysis",),
    )


def render_gap_diagnostic(clean_df: pd.DataFrame) -> None:
    """A diagnostic with two distinct denominators and no misleading causal inference."""
    heading(
        "02 / GAP DETECTOR",
        "Knowing about 988 isn't the same as using it.",
        "How much can we really say about people's willingness to call?",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return

    willingness = willingness_summary(clean_df)
    relation = knowledge_vs_willingness(clean_df)
    total = int(willingness["total_responses"])
    answered = int(willingness["answered"])
    missing = int(willingness["missing"])
    coverage = (answered / total) if total else 0.0
    pct = round(coverage * 100, 1)

    st.subheader("How many answered the willingness-to-call question?")
    st.progress(coverage)
    st.caption(f"{answered:,} of {total:,} survey responses answered ({pct:.1f}%).")
    l, r = st.columns(2)
    with l:
        st.metric("Usable willingness answers", f"{answered:,} of {total:,}")
    with r:
        st.metric("Missing or invalid answers", f"{missing:,} of {total:,}")
    st.caption(
        "The survey measures reported willingness to CALL 988, not actual use. "
        "A missing answer is not evidence of unwillingness."
    )

    st.divider()
    n = int(relation["complete_case_n"])
    gap = int(relation["gap_count"])
    st.subheader("Knowing when to use 988 vs. willingness to call")
    if n > 0:
        rate = gap / n
        if gap == 0:
            interpretation = (
                f"None of the {n:,} responses with both answers showed "
                "high knowledge AND lower willingness to call."
            )
        else:
            interpretation = (
                "of responses with both answers showed high knowledge "
                "but lower willingness to call 988."
            )
        st.markdown(
            '<div class="ba-gap-result">'
            f'<div class="ba-gap-number">{rate*100:.0f}%</div>'
            f'<div class="ba-gap-definition">{esc(interpretation)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**{gap:,} of {n:,} paired survey responses** match this pattern."
        )
        st.markdown(
            '<div class="ba-definition-note">'
            '<b>High knowledge:</b> knowing when to use 988 rated 4–5 out of 5. '
            '<b>Lower willingness:</b> willingness to call rated 0–5 out of 10.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "No responses have both a usable knowledge-of-988 rating and "
            "a willingness-to-call rating. This gap cannot be calculated."
        )

    st.markdown("### What the percentage cannot tell us")
    st.write(
        "The survey doesn't ask **why** some respondents hesitate. "
        "Trust, confidentiality, and preferring text or chat are questions "
        "worth investigating—not explanations established by this data."
    )
    st.button(
        "Explore follow-up questions in Survey Designer",
        on_click=_navigate,
        args=("Survey Designer",),
        key="gap_to_survey",
    )
    st.caption(
        "The denominator includes only responses with BOTH usable answers. "
        "For underlying distributions and correlations, open Data Explorer. "
        "These are self-reported intentions, not observed behavior."
    )


_EXCLUDED_THEME_LABELS = {
    "Other",
    "Too brief to code",
    "Positive / nothing to change",
    "No further questions / nothing to add",
    "Answered about helping others / self (not the training)",
}
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
_URL = re.compile(r"https?://\S+", re.I)


def _private_preview(text: str) -> str:
    """Additional masking for private reviewer mode, NOT anonymization."""
    s = _EMAIL.sub("[email]", str(text))
    s = _PHONE.sub("[phone]", s)
    s = _URL.sub("[link]", s)
    return s[:320] + ("…" if len(s) > 320 else "")


def _pick_themes(counts: pd.Series, max_items: int = 6) -> pd.Series:
    """Hide nonactionable labels in the chart, not from original analysis."""
    if counts.empty:
        return counts
    visible = counts[~counts.index.isin(_EXCLUDED_THEME_LABELS)]
    return visible.head(max_items)


@st.cache_data(show_spinner=False, max_entries=8, ttl=3600)
def _cached_voice_analysis(voice_df: pd.DataFrame) -> dict:
    """Analyze each distinct filtered dataset once, not on every rerun.

    Person 3's original classifier is unchanged. The subset contains only
    fields that its analyzer actually uses, so caching is inexpensive and
    invalidates when comments or the active filters/source change.
    """
    return analyze_feedback(voice_df)


def _voice_entries(
    result: dict, counts: pd.Series, *, tag_field: str, text_field: str
) -> list[dict]:
    """Build preview data in one pass over classified comments.

    Only up to five masked and distinct example comments accompany any theme;
    all original coded counts are preserved.
    """
    themes = [str(label) for label in counts.index]
    samples = {name: [] for name in themes}
    already_seen = {name: set() for name in themes}
    tagged = result["data"]
    for matched, comment in zip(tagged[tag_field], tagged[text_field]):
        if not isinstance(matched, (list, tuple)) or not isinstance(comment, str):
            continue
        candidate = _private_preview(comment)
        if not candidate.strip():
            continue
        for name in matched:
            if name not in samples or len(samples[name]) >= 5:
                continue
            if candidate not in already_seen[name]:
                already_seen[name].add(candidate)
                samples[name].append(candidate)

    return [
        {"label": str(name), "count": int(value), "comments": samples[str(name)]}
        for name, value in counts.items()
    ]


def render_participant_voices(clean_df: pd.DataFrame) -> None:
    """Interactive theme and response explorer, instant client-side hover."""
    heading(
        "03 / PARTICIPANT VOICES",
        "The people behind the patterns.",
        "Explore the topics that surfaced in written feedback. "
        "Hover over a theme to see actual matching response examples.",
    )
    if clean_df.empty:
        st.info("No responses match these filters.")
        return

    # Never hash the entire numeric analytics frame with list-valued roles.
    # These five columns contain everything Person 3's analyzer needs.
    cols = ["id", "valuable_feedback", "improvement_feedback"]
    for extra in ("county", "participant_type"):
        if extra in clean_df.columns:
            cols.append(extra)
    voice_df = clean_df[cols].copy()
    try:
        with st.spinner("Reading participant feedback…"):
            result = _cached_voice_analysis(voice_df)
    except (KeyError, ValueError):
        st.error("The written-feedback columns could not be recognized in this survey.")
        return

    modes = {
        "What to improve": ("improve_counts", "improve_themes", "improve_en"),
        "What people valued": ("learned_counts", "learned_themes", "learned_en"),
    }
    current_mode = st.radio(
        "Explore feedback",
        list(modes),
        horizontal=True,
        key="story_voice_mode",
    )
    count_field, tag_field, text_field = modes[current_mode]
    tagged = result["data"]
    comment_count = int(tagged[text_field].notna().sum())
    counts = _pick_themes(result[count_field], max_items=7)
    if counts.empty:
        st.info("No actionable coded themes are available for this selection.")
        with st.expander("All coded themes and methodology"):
            st.dataframe(
                result[count_field].rename("Theme mentions").rename_axis("Theme").reset_index(),
                hide_index=True, width="stretch",
            )
        return

    entries = _voice_entries(
        result, counts, tag_field=tag_field, text_field=text_field
    )
    st.caption(
        f"{comment_count:,} written responses · "
        f"{int(counts.sum()):,} mentions across the {len(counts)} featured themes. "
        "One comment can appear in multiple themes."
    )

    # One self-contained iframe enables hover, keyboard focus, chart expansion
    # and matching comments to update together, with no Python round trips.
    components.html(
        make_voice_explorer_html(
            entries,
            category=current_mode,
            comment_count=comment_count,
        ),
        height=760,
        scrolling=True,
    )

    with st.expander("All coded theme counts and methodology"):
        st.dataframe(
            result[count_field].rename("Theme mentions").rename_axis("Theme").reset_index(),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Person 3's original keyword-based categories are unchanged. "
            "Counts are overlapping mentions, not population proportions. "
            "Spanish translations from the original research aren't automatically "
            "mapped to new uploads because they were tied to source IDs."
        )


def render_survey_workspace(clean_df: pd.DataFrame) -> None:
    """A decision-first recommendation engine linked to all three modules."""
    heading(
        "04 / SURVEY DESIGNER",
        "What should the next survey ask?",
        "Find questions missing from this questionnaire, then connect them "
        "to the numerical patterns and written feedback in this upload.",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return

    # Person 2 and Person 3 operate on the SAME selected survey responses.
    # Person 4's original algorithm combines those signals with its own
    # keyword screen, then filters questions the uploaded form already asks.
    from survey_evidence import team_survey_findings
    evidence = team_survey_findings(clean_df)
    report = analyze_survey(clean_df, external_findings=evidence)
    coverage = report["coverage"]
    recommended = report["recommendations"]
    questions = {q["id"]: q for q in question_bank}

    direct = int((coverage["coverage"] == "Directly measured").sum())
    added = len(report["supplemental_question_columns"])
    evidence_linked = sum(
        any(source in ("person2_gap_detector", "person3_feedback_themes")
            for source in row["evidence_sources"])
        for _, row in recommended.iterrows()
    )

    st.markdown("### What the uploaded questionnaire measures")
    kpis([
        ("Dimensions with direct questions", f"{direct} of {len(coverage)}",
         "Coverage changes when new questions are uploaded"),
        ("New question columns", f"{added}",
         "Added beyond the original 20 survey fields"),
        ("Evidence-linked suggestions", f"{evidence_linked}",
         "Prompted by Person 2 or 3 findings"),
    ])
    for _, row in coverage.iterrows():
        status = str(row["coverage"])
        status_short = (
            "Direct question found" if status == "Directly measured"
            else "Partly covered" if status == "Partially measured"
            else "Not yet asked"
        )
        color = "green" if status == "Directly measured" else "gold"
        explanation = (
            "Recognized added question: " + "; ".join(row["matched_question_headers"][:2])
            if row["question_count"] else row["explanation"]
        )
        st.markdown(
            '<div class="ba-coverage" style="align-items:flex-start">'
            '<div><strong>' + esc(row["dimension"]) + '</strong>'
            '<p style="margin:5px 0 0;font-size:.84rem;line-height:1.45;'
            'color:#69796D">' + esc(explanation) + '</p></div>'
            + pill(status_short, color=color)
            + "</div>",
            unsafe_allow_html=True,
        )
    if report["unclassified_question_columns"]:
        st.caption(
            f"{len(report['unclassified_question_columns'])} additional column(s) "
            "were loaded but not confidently assigned to an accessibility dimension. "
            "The classification uses transparent matching rules, so staff should "
            "review paraphrased or unfamiliar questions."
        )
    elif added:
        st.caption(
            "Added questions were recognized from their column headings. "
            "Direct coverage does not mean every aspect of a dimension is measured."
        )

    st.divider()
    st.markdown("### Best questions for the next survey")
    st.caption(
        "Prioritized by current numerical patterns and coded feedback. "
        "If no relevant signal exists, unmeasured questionnaire topics are "
        "suggested as lower-priority design gaps. Already-asked questions are excluded."
    )
    if recommended.empty:
        st.success(
            "No unused question from the current 10-question bank matched "
            "the remaining evidence and coverage rules."
        )
    else:
        for rank, (_, suggestion) in enumerate(recommended.head(3).iterrows(), start=1):
            sources = list(suggestion.get("evidence_sources", []))
            triggered = [
                str(title) for title in suggestion.get("why_recommended", [])
            ]
            source_names = {
                "person2_gap_detector": "Knowledge / willingness analysis",
                "person3_feedback_themes": "Participant feedback themes",
                "keyword_screening": "Written-response keyword screen",
                "accessibility_audit": "Survey response coverage",
                "questionnaire_coverage": "Missing questionnaire topic",
            }
            with st.container(border=True):
                col_main, col_label = st.columns([4.3, 1], vertical_alignment="top")
                with col_main:
                    st.caption(
                        f"RECOMMENDATION {rank} · {suggestion['dimension']} · "
                        f"{suggestion['question_id']}"
                    )
                    st.markdown("### " + str(suggestion["question"]))
                    st.write("**What it would measure:** " + str(suggestion["purpose"]))
                with col_label:
                    st.caption("WHY NOW")
                    st.markdown(
                        "**Evidence-linked**" if any(
                            k in sources for k in ("person2_gap_detector",
                                                  "person3_feedback_themes")
                        ) else "**Coverage gap**"
                    )
                if triggered:
                    st.markdown(
                        "**Why this question:** " + "; ".join(triggered[:3])
                    )
                st.caption(
                    "Based on: " + ", ".join(
                        source_names.get(x, x.replace("_", " "))
                        for x in sources
                    )
                )
                with st.expander("Preview answer choices"):
                    st.caption(str(suggestion["response_type"]))
                    for option in suggestion["options"]:
                        st.write("• " + str(option))
        if len(recommended) > 3:
            with st.expander(f"See {len(recommended) - 3} more recommended questions"):
                for _, suggestion in recommended.iloc[3:].iterrows():
                    st.markdown(
                        "**" + str(suggestion["question_id"]) + " — "
                        + str(suggestion["question"]) + "**"
                    )
                    st.caption(
                        str(suggestion["dimension"]) + " · "
                        + "; ".join(suggestion["why_recommended"][:2])
                    )
                    st.divider()

    with st.expander("Build a draft survey / export questions"):
        st.caption(
            "Optional workflow: first review the evidence above. Then choose "
            "which unused proposed questions to include in a future survey."
        )
        eligible_ids = recommended["question_id"].tolist()
        selected = st.multiselect(
            "Choose proposed questions",
            options=eligible_ids,
            default=eligible_ids[:5],
            format_func=lambda qid: f"{qid} — {questions[qid]['question']}",
            key="story_survey_selected",
        )
        if selected:
            st.download_button(
                "Download the selected questions (CSV)",
                data=export_selected_questions(selected),
                file_name="everymind_followup_questions.csv",
                mime="text/csv",
                key="story_survey_download",
            )
        else:
            st.caption("Choose questions above to enable the export.")

    with st.expander("Methods, full question bank and supporting evidence"):
        st.markdown("**How these suggestions were produced**")
        st.write(
            "Person 2 supplies descriptive knowledge/willingness findings. "
            "Person 3 supplies coded feedback themes. The original Person 4 "
            "rules connect these signals and questionnaire gaps to ten proposed "
            "questions. Keyword matches are not verified participant experiences."
        )
        st.markdown("**Recognized questions in this workbook**")
        st.write(
            ", ".join(report["recognized_question_ids"])
            if report["recognized_question_ids"] else
            "No added accessibility-specific questions were recognized."
        )
        st.markdown("**All ten candidate questions**")
        st.dataframe(
            report["question_bank"][
                ["id", "dimension", "question", "purpose"]
            ],
            hide_index=True, width="stretch",
        )
        st.markdown("**Finding audit trail**")
        for finding in report["findings"]:
            st.markdown(
                "**" + str(finding["source"]).replace("_", " ").capitalize()
                + " · " + str(finding["title"]) + "**"
            )
            st.write(finding["description"])
            for limitation in finding.get("limitations", []):
                st.caption(limitation)
            st.divider()
        st.markdown("**Coverage evidence**")
        st.dataframe(
            coverage[["dimension", "coverage", "question_count", "explanation"]],
            hide_index=True, width="stretch",
        )

    st.caption(
        "Coverage reflects the questionnaire's actual columns, not an inference "
        "about respondents. A question bank is a proposal and should be reviewed "
        "by EveryMind before use. Uploading a revised workbook re-runs this audit."
    )


def render_intervention_roadmap(clean_df: pd.DataFrame) -> None:
    """Display the highest relevant candidate actions as a numbered roadmap."""
    heading(
        "05 / INTERVENTION PLANNER",
        "From findings to better training.",
        "Choose what EveryMind could try next—and how to check whether it helps.",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return

    findings = build_action_findings(clean_df)
    result = recommend_interventions(findings)
    options = result["recommendations"]
    options_by_id = {item["id"]: item for item in options}
    if not options:
        st.info("No intervention rules matched the current selection. Try different filters.")
        return

    st.subheader("Suggested next steps")
    top = options[:3]
    for number, item in enumerate(top, start=1):
        with st.container(border=True):
            lead, control = st.columns([4, 1], gap="medium")
            with lead:
                st.caption(f"STEP {number} · {item['effort']} effort estimate")
                st.markdown("### " + item["title"])
                st.write(item["summary"])
                triggers = item.get("triggered_by") or []
                if triggers:
                    st.caption("Based on: " + "; ".join(t["title"] for t in triggers[:2]))
                st.markdown("**How to check:** " + item["metric"])
            with control:
                st.checkbox(
                    "Add to plan",
                    value=item["id"] in st.session_state.get("chosen_actions", []),
                    key=f"story_action_{item['id']}",
                )

    all_other = [item for item in list_interventions() if item["id"] not in {t["id"] for t in top}]
    other_by_id = {item["id"]: item for item in all_other}
    with st.expander("Explore more intervention options"):
        additional = st.multiselect(
            "Other actions",
            options=list(other_by_id),
            default=[x for x in st.session_state.get("chosen_actions", []) if x in other_by_id],
            format_func=lambda key: other_by_id[key]["title"],
            key="story_extra_actions",
        )
        st.caption("These are optional ideas, not all supported by current findings.")
    primary = [item["id"] for item in top if st.session_state.get(f"story_action_{item['id']}", False)]
    chosen = list(dict.fromkeys(primary + additional))
    st.session_state["chosen_actions"] = chosen

    st.markdown("### Your action plan")
    if chosen:
        for idx, plan in enumerate(build_action_plan(findings, chosen), 1):
            flow_step(idx, plan["title"], plan["proposed_change"])
        st.button(
            "Create the report",
            type="primary",
            on_click=_navigate,
            args=("Reports",),
            key="plan_to_report",
        )
    else:
        st.caption("Select at least one action above to start your plan.")

    with st.expander("Why these actions? Full evidence and practical steps"):
        for item in options:
            st.markdown(f"**{item['title']}**")
            st.write(item["why"])
            st.write("Steps:")
            for step in item["steps"]:
                st.write("- " + step)
            st.caption(
                "Decision rule: " + item["change_mind"]
            )
        st.markdown("**Evidence behind recommendations**")
        for finding in findings:
            st.write("**" + finding["title"] + "** — " + finding["description"])
            for limitation in finding.get("limitations", []):
                st.caption(limitation)
    st.caption(
        "Effort is a planning estimate. Recommendations are proposals to test, not proven outcomes."
    )
    with st.expander("Advanced action planning · comparison and inclusion tools"):
        render_original_action_lab(clean_df)


def render_reports(clean_df: pd.DataFrame, summary: dict,
                   selections: dict, source_label: str) -> None:
    """Show a visual report preview and preserve Person 5's real PDF + JSON exports."""
    heading(
        "06 / REPORTS",
        "A plan they can take with them.",
        "Download an Improvement Brief with survey findings and the actions you selected.",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return

    selected = st.session_state.get("chosen_actions", [])
    findings = build_action_findings(clean_df)
    plans = build_action_plan(findings, selected)
    preview = [
        '<div class="ba-paper">',
        '<div class="paper-label">EveryMind · 988 Training</div>',
        '<h2>Improvement Brief</h2>',
        '<p>Beyond Awareness / Current Survey</p>',
        '<div class="line"></div>',
        '<div class="paper-label">Survey responses</div>',
        '<p style="font-size:1.5rem;color:#173F30;font-weight:700;margin:5px 0">'
        + esc(f"{len(clean_df):,}") + '</p>',
        '<div class="paper-label" style="margin-top:20px">Selected improvements</div>',
    ]
    if not selected:
        st.info("This report works without an action plan: you can generate a findings-only Improvement Brief right now. To add recommendations, open Intervention Planner and select improvements.")
    if plans:
        for i, plan in enumerate(plans, 1):
            preview.append(
                '<p><b>' + str(i) + '. ' + esc(plan["title"])
                + '</b><br>' + esc(plan["proposed_change"]) + '</p>'
            )
    else:
        preview.append('<p>No actions selected yet. Choose them in Intervention Planner.</p>')
    preview.append(
        '<div class="line"></div><p>Includes training metrics, evidence limits, '
        'an action plan, and an evaluation roadmap.</p></div>'
    )
    st.markdown("".join(preview), unsafe_allow_html=True)

    render_pdf_report(clean_df, summary, selections, source_label)
    if not selected:
        st.button(
            "Choose interventions",
            on_click=_navigate,
            args=("Intervention Planner",),
            key="report_to_plan",
        )

    with st.expander("Advanced export · aggregate summary (JSON)"):
        payload = {"data_source": source_label, "selections": selections, **summary}
        st.download_button(
            "Download aggregate JSON",
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
            file_name="metrics_summary.json",
            mime="application/json",
            key="story_json_export",
        )
        st.caption(
            "No respondent IDs or comments are exported. Aggregates and small groups still "
            "require appropriate approval before sharing."
        )


def render_detailed_analysis(clean_df: pd.DataFrame, summary: dict, quality: dict) -> None:
    """Numbers-first reference view. No legacy dashboards or duplicated action UI.

    All calculations still come from the shared filtered summary. Data-quality
    figures refer to the original, unfiltered uploaded source.
    """
    heading(
        "REFERENCE / DATA EXPLORER",
        "The numbers behind the findings.",
        "Explore the distributions and comparisons behind the findings, with exact counts below each chart.",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return

    section = st.selectbox(
        "Explore a dataset measure",
        [
            "Knowledge ratings",
            "Training & willingness ratings",
            "Participation",
            "Answer coverage",
            "Group comparisons",
            "Knowledge & willingness",
            "Data quality",
        ],
        key="data_explorer_section",
    )

    if section == "Knowledge ratings":
        st.markdown('<div class="ba-data-explorer-head"><h2>Knowledge ratings</h2>'
                    '<p>Matched recalled-before and current answers; agreement scale 1–5.</p></div>',
                    unsafe_allow_html=True)
        rows = []
        for topic, item in summary["knowledge"]["topics"].items():
            rows.append({
                "Topic": topic,
                "Paired answers": item["n"],
                "Recalled before": item["before_mean"],
                "Current": item["after_mean"],
                "Change": item["mean_change"],
                "Incomplete pairs": item["missing_pair_rows"],
            })
        overall = summary["knowledge"]["overall_three_topic_mean"]
        rows.append({
            "Topic": "Three-topic average",
            "Paired answers": overall["n"],
            "Recalled before": overall["before_mean"],
            "Current": overall["after_mean"],
            "Change": overall["mean_change"],
            "Incomplete pairs": overall["missing_pair_rows"],
        })
        graph_rows = [
            r for r in rows[:-1]
            if r["Recalled before"] is not None and r["Current"] is not None
        ]
        if graph_rows:
            fig = go.Figure()
            fig.add_bar(
                name="Recalled before",
                x=[r["Recalled before"] for r in graph_rows],
                y=[r["Topic"] for r in graph_rows],
                orientation="h", marker_color=BARK,
                text=[f'{r["Recalled before"]:.2f}' for r in graph_rows],
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f}/5<extra>Recalled before</extra>",
            )
            fig.add_bar(
                name="Current",
                x=[r["Current"] for r in graph_rows],
                y=[r["Topic"] for r in graph_rows],
                orientation="h", marker_color=JADE,
                text=[f'{r["Current"]:.2f}' for r in graph_rows],
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f}/5<extra>Current</extra>",
            )
            fig.update_layout(barmode="group", uniformtext=dict(minsize=11, mode="hide"))
            fig.update_xaxes(range=[0, 5.7], title="Average knowledge rating (1–5)", dtick=1)
            fig.update_yaxes(autorange="reversed", showgrid=False)
            _plot(fig, "explorer_knowledge_chart", height=340, left=205)
        else:
            st.info("No matched knowledge ratings are available in this selection.")
        st.caption("Exact paired sample sizes and values")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("Retrospective self-report. Each topic has its own matched sample; "
                   "the three-topic average requires all six ratings.")

    elif section == "Training & willingness ratings":
        options = {
            "Presenter engagement": "presenter_engagement",
            "Presenter expertise": "presenter_expertise",
            "Training organization": "training_organization",
            "Recommend training": "recommend_training",
            "Willingness to call 988": "willingness_to_call",
        }
        measure = st.selectbox("Question", list(options), key="data_explorer_rating")
        field = options[measure]
        dist = (
            summary["distributions"]["training_experience"][field]
            if field in summary["distributions"]["training_experience"]
            else summary["distributions"][field]
        )
        a, b, c = st.columns(3)
        a.metric("Usable answers", f'{dist["valid_n"]:,}')
        b.metric("Missing or invalid", f'{dist["missing_or_invalid_n"]:,}')
        c.metric("All selected rows", f'{dist["denominator_rows"]:,}')
        fig = go.Figure(go.Bar(
            x=[str(int(v["value"])) if float(v["value"]).is_integer() else str(v["value"])
               for v in dist["values"]],
            y=[v["count"] for v in dist["values"]],
            marker_color=JADE,
        ))
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title="Rating selected", type="category")
        fig.update_yaxes(title="Number of survey responses", rangemode="tozero")
        _plot(fig, "explorer_rating_chart", height=320, left=70)
        st.markdown("#### Exact score counts")
        st.dataframe(
            pd.DataFrame([
                {"Score": int(item["value"]) if float(item["value"]).is_integer() else item["value"],
                 "Responses": item["count"],
                 "Share of valid answers": (
                     round(item["share"] * 100, 1) if item["share"] is not None else None
                 )}
                for item in dist["values"]
            ]).rename(columns={"Share of valid answers": "Share of valid answers (%)"}),
            hide_index=True, width="stretch",
        )
        st.caption("Training items use 1–5 agreement ratings; recommendation and willingness "
                   "questions use 0–10 scales. Self-reported intentions are not behavior.")

    elif section == "Participation":
        dimension = st.selectbox(
            "Group by", ["County", "Participant role", "Survey language", "Training date"],
            key="data_explorer_participation",
        )
        selected = {
            "County": "county", "Participant role": "role", "Survey language": "language",
        }
        if dimension == "Training date":
            records = summary["coverage"]["training_date"]["dates"]
            frame = pd.DataFrame(
                [{"Date": row["date"][:10], "Survey rows": row["n"]}
                 for row in records]
            )
        else:
            groups = summary["coverage"][selected[dimension]]["groups"]
            frame = pd.DataFrame([
                {
                    "Category": row["category"],
                    "Survey rows": row["n"],
                    "Rows share (%)": round(100 * row["share_of_rows"], 1)
                    if row["share_of_rows"] is not None else None,
                    "Answered call question": row["willingness_valid_n"],
                    "Call answer coverage (%)": round(100 * row["willingness_response_rate"], 1)
                    if row["willingness_response_rate"] is not None else None,
                }
                for row in groups
            ])
        if frame.empty:
            st.info("No categorized responses for this selection.")
        else:
            top = frame.sort_values("Survey rows", ascending=False).head(12)
            cat = "Date" if dimension == "Training date" else "Category"
            fig = go.Figure(go.Bar(
                x=top["Survey rows"].tolist(),
                y=top[cat].astype(str).tolist(),
                orientation="h", marker_color=JADE,
            ))
            fig.update_layout(showlegend=False)
            fig.update_yaxes(autorange="reversed", showgrid=False)
            fig.update_xaxes(title="Survey responses", rangemode="tozero")
            label_width = min(290, max(150, max(len(str(x)) for x in top[cat])*7 + 30))
            _plot(fig, "explorer_participation_chart",
                  height=max(290, len(top)*40+110), left=label_width)
            st.caption("Exact counts and coverage")
            st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Counts describe survey rows, not population representation. "
                   "Participant roles can overlap.")

    elif section == "Answer coverage":
        labels = {
            "before_identify": "Identify a crisis · recalled before",
            "after_identify": "Identify a crisis · current",
            "before_describe": "Describe 988 · recalled before",
            "after_describe": "Describe 988 · current",
            "before_when": "When to use 988 · recalled before",
            "after_when": "When to use 988 · current",
            "willingness_to_call": "Willingness to call 988",
            "recommend_training": "Recommend training",
        }
        frame = pd.DataFrame([
            {
                "Question": labels.get(item["field"], item["field"].replace("_", " ").capitalize()),
                "Usable": item["usable_n"],
                "Blank": item["source_missing_n"],
                "Invalid": item["invalid_or_unusable_n"],
                "Total": item["denominator_rows"],
            }
            for item in summary["missingness"]
        ])
        top = (
            frame.assign(unusable=frame["Blank"] + frame["Invalid"])
            .sort_values("unusable", ascending=False).head(12)
        )
        fig = go.Figure()
        fig.add_bar(
            name="Blank", x=top["Blank"], y=top["Question"],
            orientation="h", marker_color=BARK,
            hovertemplate="%{y}<br>%{x} blank<extra></extra>",
        )
        fig.add_bar(
            name="Invalid / unusable", x=top["Invalid"], y=top["Question"],
            orientation="h", marker_color=JADE,
            hovertemplate="%{y}<br>%{x} invalid<extra></extra>",
        )
        fig.update_layout(barmode="stack")
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(title="Survey responses without a usable answer", rangemode="tozero")
        _plot(fig, "explorer_coverage_chart",
              height=max(390, len(top)*40+110), left=260)
        st.caption("Exact answer coverage")
        st.dataframe(frame, hide_index=True, width="stretch")
        st.caption("Blank and invalid answers are reported separately. Neither implies reluctance.")

    elif section == "Group comparisons":
        left, right = st.columns(2)
        with left:
            group = st.selectbox(
                "Compare by", ["county", "role", "language"],
                format_func=lambda k: {"county": "Training county",
                                       "role": "Participant role",
                                       "language": "Survey language"}[k],
                key="data_explorer_compare_group",
            )
        with right:
            topic = st.selectbox(
                "Knowledge topic", list(summary["knowledge"]["topics"]),
                key="data_explorer_compare_topic",
            )
        frame = pd.DataFrame([
            {
                "Group": item["category"],
                "Survey rows": item["n"],
                "Paired answers": item["knowledge"]["topics"][topic]["n"],
                "Recalled before": item["knowledge"]["topics"][topic]["before_mean"],
                "Current": item["knowledge"]["topics"][topic]["after_mean"],
                "Change": item["knowledge"]["topics"][topic]["mean_change"],
                "Small paired group": item["knowledge"]["topics"][topic]["suppressed"],
            }
            for item in summary["group_comparisons"][group]
        ])
        if frame.empty:
            st.info("No groups match the current selection.")
        else:
            chart_frame = frame.dropna(subset=["Change"]).sort_values("Change").tail(12)
            if not chart_frame.empty:
                fig = go.Figure(go.Bar(
                    x=chart_frame["Change"].tolist(),
                    y=chart_frame["Group"].astype(str).tolist(),
                    orientation="h", marker_color=BARK,
                ))
                fig.update_layout(showlegend=False)
                fig.update_xaxes(title="Mean rating change (points)")
                label_width = min(290, max(150, max(len(str(x)) for x in chart_frame["Group"])*7 + 30))
                _plot(fig, "explorer_comparison_chart",
                      height=max(280, len(chart_frame)*40+110), left=label_width)
            else:
                st.info("No group meets the minimum paired-response threshold for this topic.")
            st.caption("Exact group comparisons, with suppressed means left blank")
            st.dataframe(frame, hide_index=True, width="stretch")
        st.caption(f"Mean comparisons are suppressed when fewer than {summary['min_group_n']} "
                   "paired responses are available. Role groups may overlap.")

    elif section == "Knowledge & willingness":
        call = willingness_summary(clean_df)
        related = knowledge_vs_willingness(clean_df)
        usable = int(call["answered"])
        n = int(call["total_responses"])
        paired = int(related["complete_case_n"])
        gap = int(related["gap_count"])
        st.dataframe(
            pd.DataFrame([
                {"Measure": "Survey rows", "Count": n},
                {"Measure": "Answered willingness question", "Count": usable},
                {"Measure": "Answered knowledge and willingness", "Count": paired},
                {"Measure": "High knowledge / lower willingness", "Count": gap},
            ]),
            hide_index=True, width="stretch",
        )
        st.markdown("#### Knowledge versus willingness — response counts")
        heat = related["heatmap"]
        fig = go.Figure(go.Heatmap(
            z=heat.to_numpy(), x=[str(c) for c in heat.columns],
            y=[str(r) for r in heat.index], colorscale=[
                [0, "#F5F7F0"], [0.5, "#94BDA1"], [1, "#237557"]
            ], colorbar=dict(title="Responses"),
            hovertemplate="Knowledge %{y}<br>Willingness %{x}<br>%{z} responses<extra></extra>",
        ))
        fig.update_layout(showlegend=False)
        fig.update_xaxes(title="Willingness score (0–10)", type="category")
        fig.update_yaxes(title="Knowledge score (1–5)", type="category")
        _plot(fig, "explorer_gap_heatmap", height=310, left=70)
        with st.expander("View exact cross-tabulated counts"):
            st.dataframe(heat, width="stretch")
        score_counts = call["score_distribution"]
        st.markdown("#### Willingness scores")
        st.dataframe(
            pd.DataFrame([{"Score": k, "Responses": v}
                          for k, v in score_counts.items()]),
            hide_index=True, width="stretch",
        )
        corr = related["spearman_correlation"]
        if corr is not None and not pd.isna(corr):
            st.caption(f"Spearman correlation among usable paired answers: {float(corr):.3f}. "
                       "Association is descriptive, not causal.")
        else:
            st.caption("Correlation not available for this selection.")

    elif section == "Data quality":
        st.caption("This section reports diagnostics for the FULL uploaded workbook "
                   "before page filters, not only the current selection.")
        overview = [
            ("Source survey rows", quality.get("original_row_count")),
            ("Cleaned survey rows", quality.get("clean_row_count")),
            ("Distinct nonblank IDs", quality.get("distinct_nonmissing_ids")),
            ("Fully paired knowledge rows", quality.get("fully_paired_knowledge_rows")),
            ("Valid willingness answers", quality.get("willingness_valid_rows")),
            ("Training dates", quality.get("distinct_training_dates")),
            ("Counties", quality.get("county_count")),
        ]
        st.dataframe(
            pd.DataFrame([{"Measure": label, "Count": value} for label, value in overview]),
            hide_index=True, width="stretch",
        )
        for field, title in [
            ("duplicate_ids", "Duplicate-ID checks"),
            ("invalid_values", "Invalid or nonstandard values"),
            ("date_failures", "Date parsing failures"),
            ("normalization_counts", "Normalization checks"),
        ]:
            values = quality.get(field, {})
            if isinstance(values, dict) and values:
                st.markdown(f"#### {title}")
                st.dataframe(
                    pd.DataFrame([
                        {"Metric": str(k).replace("_", " ").capitalize(),
                         "Count": value if isinstance(value, (int, float)) else str(value)}
                        for k, value in values.items()
                    ]),
                    hide_index=True, width="stretch",
                )
        if quality.get("missingness"):
            st.markdown("#### Missingness in the complete source")
            frame = pd.DataFrame.from_dict(quality["missingness"], orient="index")
            frame.index.name = "Question"
            st.dataframe(frame.reset_index(), hide_index=True, width="stretch")

