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

    improved = [label for label, item in usable
                if float(item["after_mean"]) > float(item["before_mean"])]
    if improved:
        takeaway(
            f"Higher current ratings in {len(improved)} of {len(usable)} topics.",
            "Only matched recalled-before and current ratings enter each comparison. "
            "An observed difference is not evidence of a causal effect.",
            label="HOW TO READ IT",
        )
    else:
        takeaway(
            "The displayed topics do not show higher current averages.",
            "Inspect paired responses before concluding anything about training effects.",
            label="HOW TO READ IT",
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


def _draw_theme_donut(counts: pd.Series, selected: str, key: str) -> None:
    """Chart proportions are theme mentions, never percentages of participants."""
    palette = [FOREST, JADE, BARK, "#6B9875", "#D4B58C", "#B7C9B3"]
    colors = [FOREST if name == selected else palette[i % len(palette)]
              for i, name in enumerate(counts.index)]
    fig = go.Figure(go.Pie(
        labels=list(counts.index),
        values=[int(v) for v in counts.values],
        hole=.74,
        textinfo="none",
        sort=False,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=3)),
        hovertemplate="%{label}<br>%{value} theme matches<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        annotations=[dict(
            text=f"<b>{len(counts)} themes</b><br>to explore",
            x=.5, y=.5, showarrow=False,
            font=dict(size=15, color=INK),
            align="center",
        )],
        margin=dict(l=12, r=12, t=9, b=9),
        height=292,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    _lock_figure(fig)
    st.plotly_chart(
        fig, key=key, width="stretch", theme=None, config=PLOT_CONFIG,
    )


def render_participant_voices(clean_df: pd.DataFrame) -> None:
    heading(
        "03 / PARTICIPANT VOICES",
        "The responses behind the numbers.",
        "Explore themes in what people valued and what they want to change.",
    )
    if clean_df.empty:
        st.info("No responses match these filters.")
        return
    try:
        result = analyze_feedback(clean_df)
    except (KeyError, ValueError):
        st.error("The feedback columns could not be recognized in this survey.")
        return

    modes = {
        "What to improve": ("improve_counts", "improve_themes", "improve_en"),
        "What people valued": ("learned_counts", "learned_themes", "learned_en"),
    }
    current_mode = st.radio(
        "Feedback category",
        list(modes),
        horizontal=True,
        label_visibility="collapsed",
        key="story_voice_mode",
    )
    count_field, tag_field, text_field = modes[current_mode]
    tagged = result["data"]
    count = int(tagged[text_field].notna().sum())
    counts = _pick_themes(result[count_field])
    if counts.empty:
        st.info("No coded themes in the current survey selection.")
        return

    st.caption(
        f"{count:,} responses with comments. Themes overlap; the donut represents "
        "theme mentions across the displayed categories, not shares of participants."
    )

    state_key = "voice_theme_improve" if current_mode == "What to improve" else "voice_theme_learned"
    if st.session_state.get(state_key) not in counts.index:
        st.session_state[state_key] = str(counts.index[0])
    selected = st.session_state[state_key]
    chart, legend = st.columns([1.15, 1.25], gap="large")
    with chart:
        _draw_theme_donut(counts, selected, f"voice_donut_{tag_field}")
    with legend:
        st.markdown("#### Choose a theme")
        for idx, (label, value) in enumerate(counts.items()):
            c1, c2 = st.columns([5, 1], gap="small")
            with c1:
                st.button(
                    label,
                    type="primary" if selected == label else "secondary",
                    use_container_width=True,
                    key=f"voice_choice_{tag_field}_{idx}",
                    on_click=lambda which=label, k=state_key: st.session_state.update({k: which}),
                )
            with c2:
                st.markdown(
                    f'<div style="color:{MUTED};text-align:right;'
                    f'padding:11px 0;font-size:.81rem">{int(value)}</div>',
                    unsafe_allow_html=True,
                )

    selected = st.session_state[state_key]
    matching = tagged.loc[
        tagged[tag_field].apply(lambda x: isinstance(x, list) and selected in x),
        text_field,
    ].dropna()

    st.markdown("### " + selected)
    st.caption(f"{len(matching):,} matching comments · Rule-based coding, not human-verified.")
    st.markdown(
        "Responses are stored only in the current private application session. "
        "Individual comments may include sensitive details."
    )

    show = st.checkbox(
        "Review matching comment examples privately",
        value=False,
        key=f"private_voice_{tag_field}",
    )
    if show:
        st.warning(
            "Private review only. Automated name, email and phone masking is incomplete; "
            "do not screenshot, share, or export text without an approved privacy review."
        )
        for j, text in enumerate(matching.head(5), start=1):
            with st.container(border=True):
                st.caption(f"Comment {j} · masked preview")
                st.write(_private_preview(text))
    else:
        takeaway(
            "Explore themes without exposing private comments.",
            "Select a theme above, then opt into private review only if you are authorized.",
            label="PRIVACY FIRST",
        )

    with st.expander("Full coded theme counts and method"):
        st.dataframe(
            result[count_field].rename("Theme matches").rename_axis("Theme").reset_index(),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Counts describe rule-based matches. One comment can match multiple themes. "
            "Spanish translations in the original research were tied to source IDs and "
            "have not been automatically applied to new uploads. Manual checking is still needed."
        )


def render_survey_workspace(clean_df: pd.DataFrame) -> None:
    """Build a future survey, not a table of metadata."""
    heading(
        "04 / SURVEY DESIGNER",
        "Ask what the original survey couldn't.",
        "Choose a small set of better questions for the next training.",
    )
    if clean_df.empty:
        st.info("No responses match the current filters.")
        return
    report = analyze_survey(clean_df)
    coverage = report["coverage"]
    recommended = report["recommendations"]
    questions = {q["id"]: q for q in question_bank}

    st.subheader("Where the current survey stops")
    for _, row in coverage.iterrows():
        status = str(row["coverage"])
        badge = "Partly measured" if "Partially" in status else "Not measured" if "Not" in status else status
        st.markdown(
            '<div class="ba-coverage"><strong>' + esc(row["dimension"]) + '</strong>'
            + pill(badge, color="gold" if "Not" in status else "green")
            + "</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "These are questions the survey does not directly ask, not proof that any barrier exists."
    )

    st.markdown("### Questions worth adding")
    st.caption("Based on the current survey's coverage and coded requests.")
    suggestions = recommended.head(3)
    if suggestions.empty:
        st.info("No question matched the current detection rules. You can still choose from the full bank.")
    else:
        for rank, (_, suggestion) in enumerate(suggestions.iterrows(), start=1):
            with st.container(border=True):
                st.caption(f"QUESTION {rank} · {suggestion['dimension']}")
                st.markdown("**" + suggestion["question"] + "**")
                why = suggestion.get("why_recommended", [])
                if isinstance(why, list) and why:
                    st.caption("Suggested because: " + "; ".join(map(str, why[:2])))

    default_ids = recommended["question_id"].tolist()
    selected = st.multiselect(
        "Build your draft survey",
        options=list(questions),
        default=default_ids,
        format_func=lambda qid: questions[qid]["question"],
        key="story_survey_selected",
    )
    if selected:
        st.download_button(
            "Download selected questions (CSV)",
            data=export_selected_questions(selected),
            file_name="everymind_followup_questions.csv",
            mime="text/csv",
            type="primary",
            key="story_survey_download",
        )
    else:
        st.caption("Choose at least one question to enable the download.")

    with st.expander("Full question bank, answer choices and evidence"):
        for q in question_bank:
            st.markdown(f"**{q['id']} — {q['question']}**")
            st.caption(q["dimension"] + " · " + q["purpose"])
            st.write("Options: " + "; ".join(q["options"]))
            st.divider()
        st.markdown("**Observed findings and caveats**")
        for finding in report["findings"]:
            st.write(f"**{finding['title']}** — {finding['description']}")
            for note in finding.get("limitations", []):
                st.caption(note)
        st.dataframe(coverage, hide_index=True, width="stretch")
    st.caption(
        "Questions are proposals, not validated instruments. EveryMind should "
        "review them before participant use."
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
        graph_rows = rows[:-1]
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

