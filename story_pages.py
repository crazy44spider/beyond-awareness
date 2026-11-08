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
    FOREST, GOLD, GRID, INK, JADE, MUTED, SAGE,
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


def _plot(fig: go.Figure, key: str, *, height: int = 300, left: int = 24) -> None:
    """Compact readable charts. Horizontal labels are never placed below the fold."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Arial, sans-serif", size=12, color=INK),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=left, r=22, t=30, b=38),
        height=height,
        showlegend=True,
        legend=dict(
            orientation="h", y=1.13, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11),
        ),
        hovermode="closest",
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    st.plotly_chart(
        fig, key=key, width="stretch", theme=None,
        config={"displaylogo": False, "displayModeBar": False, "responsive": True},
    )


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
        ("Answered the call question", _pct(rate), f"{answered:,} answered; {missing:,} missing or invalid"),
    ])

    knowledge = summary["knowledge"]["topics"]
    higher = [
        label for label, stats in knowledge.items()
        if stats["n"] and stats["mean_change"] is not None and stats["mean_change"] > 0
    ]
    if higher:
        takeaway(
            "Participants generally rated their knowledge higher after training.",
            "This is a retrospective self-report, not proof the training caused the change.",
            label="WHAT THE SURVEY SUGGESTS",
        )
    else:
        takeaway(
            "Knowledge outcomes need a closer look.",
            "Not enough paired ratings are available to summarize higher knowledge.",
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
            line=dict(color="#BCD9C5", width=8), showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[before], y=[y], mode="markers",
            marker=dict(color="#B5C4B6", size=15, line=dict(color="white", width=2)),
            showlegend=index == 0, name="Recalled before",
            hovertemplate="%{y}: %{x:.2f}<extra>Recalled before</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[after], y=[y], mode="markers",
            marker=dict(color=JADE, size=17, line=dict(color="white", width=2)),
            showlegend=index == 0, name="Current",
            hovertemplate="%{y}: %{x:.2f}<extra>Current</extra>",
        ))
    fig.update_layout(
        title=dict(text="Recalled-before vs. current ratings", x=.02, font=dict(size=15)),
    )
    fig.update_xaxes(range=[.8, 5.2], title="Agreement score, 1–5", dtick=1)
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=[translated.get(name, name) for name, _ in usable][::-1],
        showgrid=False,
        tickfont=dict(size=12),
        automargin=True,
    )
    _plot(fig, "story_learning_dumbbell", height=285, left=175)

    improved = [label for label, item in usable
                if float(item["after_mean"]) > float(item["before_mean"])]
    if improved:
        takeaway(
            "Current self-ratings are higher in the displayed topics.",
            f"Higher averages in {len(improved)} of {len(usable)} knowledge areas. "
            "The same participant must have answered both ratings to enter each comparison.",
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
    if st.button(
        "See distributions and group comparisons",
        key="outcomes_to_details",
        on_click=_navigate,
        args=("Detailed Analysis",),
    ):
        pass


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

    st.subheader("First, who answered?")
    st.progress(coverage)
    l, r = st.columns(2)
    with l:
        st.metric("Answered the call question", f"{answered:,}", help=f"{pct}% of {total:,}")
    with r:
        st.metric("No usable call answer", f"{missing:,}")
    st.caption(
        "The unanswered responses cannot be interpreted as unwillingness. "
        "Some survey versions may not have asked the question."
    )

    st.divider()
    st.subheader("Among people who answered both questions")
    n = int(relation["complete_case_n"])
    gap = int(relation["gap_count"])
    if n > 0:
        rate = gap / n
        left, right = st.columns([1, 2], gap="large")
        with left:
            st.markdown(
                f'<div style="font:600 3.7rem Georgia,serif;color:{FOREST};'
                f'letter-spacing:-.07em;line-height:1.1">{rate*100:.0f}%</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{gap:,} of {n:,} complete answers")
        with right:
            takeaway(
                "High knowledge, but lower willingness to call.",
                "These respondents rated knowing when to use 988 at 4–5 "
                "and willingness to call at 0–5. The survey doesn't explain why.",
                label="DEFINED PATTERN",
            )
    else:
        st.info("There are not enough complete knowledge-and-call responses to compare.")

    st.markdown("### What could explain the gap?")
    st.write(
        "Trust, privacy, preferring text, uncertainty about needing help—"
        "all are possibilities **not measured directly** by this survey."
    )
    st.button(
        "See questions that could fill the gaps",
        on_click=_navigate,
        args=("Survey Designer",),
        key="gap_to_survey",
    )
    st.caption(
        "For cross-tabulations, score distributions and the Spearman correlation, "
        "use Detailed Analysis. The relationship is observational."
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
    palette = [FOREST, JADE, "#4B9971", "#8FBFA0", GOLD, "#C6D3BF"]
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
    st.plotly_chart(
        fig, key=key, width="stretch", theme=None,
        config={"displayModeBar": False, "displaylogo": False},
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
    """Original deep-dive functions preserved verbatim for analysts."""
    heading(
        "REFERENCE / DETAILED ANALYSIS",
        "Every number, if you need it.",
        "Explore distributions, group comparisons and data quality without "
        "cluttering the main story.",
    )
    if clean_df.empty:
        st.info("No responses match these filters.")
        return

    tabs = st.tabs([
        "Knowledge details", "Training ratings", "Representation",
        "Response coverage", "Group comparisons", "Data quality",
        "Knowledge & call", "Original overview", "Action tools",
    ])
    with tabs[0]:
        render_knowledge(summary)
    with tabs[1]:
        render_experience(clean_df, summary)
    with tabs[2]:
        render_representation(summary)
    with tabs[3]:
        render_missingness(summary)
    with tabs[4]:
        render_comparisons(summary)
    with tabs[5]:
        render_quality(quality)
    with tabs[6]:
        willing = willingness_summary(clean_df)
        comparison = knowledge_vs_willingness(clean_df)
        st.markdown("#### Knowledge versus willingness")
        st.write(
            f"Complete paired answers: {comparison['complete_case_n']:,}; "
            f"high-knowledge/lower-willingness cases: {comparison['gap_count']:,}."
        )
        st.dataframe(comparison["heatmap"], width="stretch")
        st.dataframe(
            pd.DataFrame(
                list(willing["score_distribution"].items()),
                columns=["Score", "Responses"],
            ),
            hide_index=True,
            width="stretch",
        )
        corr = comparison["spearman_correlation"]
        if corr is not None and not pd.isna(corr):
            st.write(f"Spearman correlation: {float(corr):.3f}")
        st.caption(
            "Only matched, usable answers are included. No causal conclusion follows."
        )

    with tabs[7]:
        # The original full-detail overview remains accessible, not deleted.
        render_original_overview(summary)
    with tabs[8]:
        # Preserve Person 5's comparison mode and inclusive-action lens, too.
        render_original_action_lab(clean_df)
