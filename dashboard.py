from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui_styles import inject_styles, intro, stat_cards, focus_card

BARK = "#A17C59"
JADE = "#287859"
UMBER = "#9E764C"
MUTED = "#64786B"
TOPIC_LIMIT = "Retrospective self-report; this comparison does not establish a causal training effect."
LABELS = {
    "before_identify": "Identify crisis · recalled before",
    "after_identify": "Identify crisis · current",
    "before_describe": "Describe 988 · recalled before",
    "after_describe": "Describe 988 · current",
    "before_when": "Know when to use 988 · recalled before",
    "after_when": "Know when to use 988 · current",
    "presenter_engagement": "Presenter engagement",
    "presenter_expertise": "Presenter expertise",
    "training_organization": "Training organization",
    "recommend_training": "Recommend training",
    "willingness_to_call": "Willingness to call 988",
    "valuable_feedback": "Most valuable learning",
    "improvement_feedback": "Suggestions for improvement",
    "participant_type": "Participant role",
    "training_date": "Training date",
    "start_time": "Survey start time",
    "completion_time": "Survey completion time",
    "county": "Training county", "language": "Language", "id": "Survey ID",
}
UNMEASURED_BARRIERS = [
    "Cultural stigma", "Financial or practical access", "Preferred call/text/chat channel",
    "Institutional trust", "Comfort with confidentiality", "Psychological comfort",
]


def percent(value):
    return "N/A" if value is None else f"{value:.1%}"


def number(value, signed=False):
    return "N/A" if value is None else format(value, "+.2f" if signed else ".2f")


def style_app():
    """Install the shared accessible, light-colored app theme."""
    inject_styles()


def _chart(fig, key, *, percent_axis=False, height=340, left=68):
    """Legacy visualizations use the same locked, accessible axes as new pages."""
    showlegend = (
        bool(fig.layout.showlegend) if fig.layout.showlegend is not None
        else sum(bool(t.name) and t.showlegend is not False for t in fig.data) > 1
    )
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI, Arial, sans-serif", size=13, color="#284333"),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        margin=dict(l=left, r=30, t=62 if showlegend else 26, b=55),
        legend=dict(orientation="h", y=1.16, x=0,
                    itemclick=False, itemdoubleclick=False),
        showlegend=showlegend,
        height=height,
        hovermode="closest",
        dragmode=False,
        clickmode="none",
        colorway=[JADE, BARK, "#D5B48D"],
        hoverlabel=dict(bgcolor="#F7F8F2", font=dict(color="#284333")),
    )
    if percent_axis:
        fig.update_yaxes(range=[0, 100], title="Share of paired answers (%)")
    fig.update_xaxes(fixedrange=True, automargin=True, gridcolor="#E5EBE3")
    fig.update_yaxes(fixedrange=True, automargin=True, gridcolor="#E5EBE3")
    st.plotly_chart(
        fig, width="stretch", theme=None, key=key,
        config={
            "displaylogo": False,
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
            "editable": False,
            "showAxisDragHandles": False,
            "showAxisRangeEntryBoxes": False,
            "responsive": True,
        },
    )


def _bar(records, category, value, *, x_title, color=BARK, horizontal=False):
    labels = [str(row[category]) for row in records]
    values = [row[value] for row in records]
    fig = go.Figure(go.Bar(
        x=values if horizontal else labels, y=labels if horizontal else values,
        orientation="h" if horizontal else "v", marker_color=color,
        text=values, textposition="auto", hovertemplate="%{y}: %{x}<extra></extra>" if horizontal else None,
    ))
    if horizontal:
        fig.update_xaxes(title=x_title, rangemode="tozero")
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_yaxes(title=x_title, rangemode="tozero")
    return fig


def render_overview(summary):
    """Lead with the story and the survey's blind spots; retain details below."""
    overview = summary["overview"]
    n = int(overview["survey_rows"])
    knowledge = summary["knowledge"]["topics"]
    positive = sum(
        1 for stats in knowledge.values()
        if stats["n"] > 0 and stats["mean_change"] is not None
        and stats["mean_change"] > 0
    )
    assessed = sum(1 for stats in knowledge.values() if stats["n"] > 0)
    response_rate = overview["willingness_response_rate"]
    missing = int(overview["willingness_missing_or_invalid_n"])

    intro(
        "THE TRAINING STORY · AT A GLANCE",
        "What the training tells us",
        "What participants learned—and what to improve.",
    )

    stat_cards([
        {
            "icon": "💜",
            "tone": "lilac",
            "label": "Survey responses",
            "value": f"{n:,}",
            "detail": "Survey responses",
        },
        {
            "icon": "🌱",
            "tone": "mint",
            "label": "Knowledge ratings improved",
            "value": f"{positive} of {assessed}" if assessed else "Not available",
            "detail": "Across three topics",
        },
        {
            "icon": "💬",
            "tone": "peach",
            "label": "Answered the call question",
            "value": percent(response_rate),
            "detail": f"{missing:,} unanswered or invalid",
        },
    ])

    st.write("")
    chart_col, story_col = st.columns([1.6, 1], gap="large")

    with chart_col:
        st.subheader("Reported knowledge")
        st.caption("Before vs. after · self-reported")
        records = list(knowledge.items())
        if records and any(item["n"] > 0 for _, item in records):
            fig = go.Figure()
            labels = [name for name, _ in records]
            fig.add_bar(
                name="Recalled before",
                x=labels,
                y=[item["before_mean"] for _, item in records],
                marker_color="#D9C3A8",
                marker_line_width=0,
            )
            fig.add_bar(
                name="Current",
                x=labels,
                y=[item["after_mean"] for _, item in records],
                marker_color="#287859",
                marker_line_width=0,
            )
            fig.update_layout(barmode="group", bargap=.28)
            fig.update_yaxes(range=[0, 5], title=None, gridcolor="#E4EBDF")
            fig.update_xaxes(title=None, tickfont=dict(size=11))
            _chart(fig, "overview_knowledge", height=320)
        else:
            st.info("No paired knowledge ratings are available in this selection.")

    with story_col:
        focus_card(
            "WHAT'S MISSING",
            "Would people actually reach out?",
            "The survey asks whether people would CALL 988. "
            "It doesn't ask whether they would rather text or chat, "
            "or how comfortable they feel asking for help."
        )
        st.caption(
            f"Of {n:,} selected responses, {missing:,} have no usable answer to the call-intent item. "
            "We cannot interpret blank answers as unwillingness."
        )

    with st.expander("See the numbers"):
        st.write(
            "Each knowledge comparison uses only responses with both a recalled-before "
            "and a current rating. A higher average rating is descriptive; it does not "
            "prove that training caused the change."
        )
        table = [
            {
                "Topic": topic,
                "Paired responses": stats["n"],
                "Recalled-before mean": stats["before_mean"],
                "Current mean": stats["after_mean"],
                "Change (points)": stats["mean_change"],
                "Incomplete pairs": stats["missing_pair_rows"],
            }
            for topic, stats in knowledge.items()
        ]
        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
        st.caption(
            "The call-intent response rate is usable answers divided by all selected rows. "
            "Missing answers and unusable values are not treated as unwillingness."
        )

    with st.expander("More metrics"):
        # Preserve all six indicators from the previous Overview, now optional.
        extra = st.columns(3)
        for col, label, value in zip(
            extra,
            ["Survey rows", "Training dates", "Fully paired knowledge rows"],
            [
                overview["survey_rows"],
                overview["distinct_training_dates"],
                overview["fully_paired_knowledge_rows"],
            ],
        ):
            col.metric(label, f"{value:,}")
        extra = st.columns(3)
        extra[0].metric(
            "Willingness answer coverage",
            percent(overview["willingness_response_rate"]),
        )
        extra[1].metric("Training counties", overview["county_count"])
        extra[2].metric("Role categories", overview["role_category_count"])
        st.caption(
            "These figures use the current filters. Survey rows and distinct IDs "
            "do not necessarily represent distinct people."
        )

    if n < summary["min_group_n"]:
        st.warning(
            f"Only {n} responses match these filters. "
            f"Comparisons below {summary['min_group_n']} paired responses need extra caution."
        )
    st.caption(
        "Survey answers show what respondents reported—not the needs of every person "
        "in a community, nor confirmed cultural or practical barriers."
    )


def render_knowledge(summary):
    """Full-width comparisons avoid clipped labels in three narrow cards."""
    st.subheader("Knowledge distributions")
    st.caption("Ratings: 1 = strongly disagree · 5 = strongly agree. "
               "Only respondents answering both versions of each question are counted.")
    for i, (topic, stats) in enumerate(summary["knowledge"]["topics"].items()):
        st.markdown(f"#### {topic}")
        paired = summary["distributions"]["knowledge_paired"][topic]
        fig = go.Figure()
        for period, label, color in [
            ("before", "Recalled before", BARK),
            ("after", "Current", JADE),
        ]:
            fig.add_bar(
                name=label,
                x=[str(int(r["value"])) for r in paired[period]["values"]],
                y=[None if r["share"] is None else r["share"] * 100
                   for r in paired[period]["values"]],
                marker_color=color,
                hovertemplate="%{y:.1f}% of paired answers<extra>" + label + "</extra>",
            )
        fig.update_layout(barmode="group", bargap=.25)
        fig.update_xaxes(title="Agreement rating (1–5)", type="category")
        _chart(fig, f"knowledge_{i}", percent_axis=True, height=325)
        change = number(stats["mean_change"], signed=True)
        st.markdown(
            f"**Average rating change: {change} points** · "
            f"{stats['n']:,} paired responses · "
            f"{stats['missing_pair_rows']:,} incomplete pairs"
        )
        st.caption(
            f"Reported higher: {percent(stats['share_up'])}; "
            f"same: {percent(stats['share_same'])}; "
            f"lower: {percent(stats['share_down'])}. {TOPIC_LIMIT}"
        )
        st.divider()
    overall = summary["knowledge"]["overall_three_topic_mean"]
    st.subheader("Overall three-topic average")
    st.write(
        f"Recalled before: **{number(overall['before_mean'])}** → "
        f"Current: **{number(overall['after_mean'])}** · "
        f"Mean difference: **{number(overall['mean_change'], signed=True)}**"
    )
    st.caption(
        f"{overall['n']:,} responses had all six ratings; "
        f"{overall['missing_pair_rows']:,} did not. Equal-weight averages, "
        "not a validated composite scale. " + TOPIC_LIMIT
    )


def _rating_chart(dist, key, label, scale_max):
    _chart(_bar(dist["values"], "value", "count", x_title="Valid answers", color=JADE), key)
    st.caption(f"Question: {label}. Scale 0–{scale_max}. Counts among {dist['valid_n']} valid answers out of {dist['denominator_rows']} rows; {dist['missing_or_invalid_n']} missing/invalid. Self-reported intention does not establish behavior.")


def render_experience(clean_df, summary):
    st.subheader("Training experience")
    st.caption("Use a full-width distribution for each training question.")
    for i, (field, dist) in enumerate(
        summary["distributions"]["training_experience"].items()
    ):
        st.markdown(f"#### {LABELS[field]}")
        _chart(
            _bar(dist["values"], "value", "count",
                 x_title="Number of valid answers", color=JADE),
            f"experience_{i}", height=295,
        )
        invalid = int(clean_df[f"{field}_invalid"].sum())
        st.caption(
            f"Agreement 1–5: {dist['valid_n']:,} usable answers of "
            f"{dist['denominator_rows']:,} survey responses; "
            f"{dist['missing_or_invalid_n']:,} missing/invalid."
        )
        if invalid:
            st.warning(f"{invalid:,} nonstandard answers were excluded from scoring.")
        st.divider()
    for key, label, question in [
        ("recommend_training", "Recommend training", "Likelihood of recommending training"),
        ("willingness_to_call", "Willingness to call 988", "Likelihood of calling 988"),
    ]:
        st.markdown(f"#### {label}")
        _rating_chart(summary["distributions"][key], key + "_legacy", question, 10)


def render_representation(summary):
    st.subheader("Participation & representation")
    st.caption("Counts describe survey responses, not the composition of the population.")
    for field, title in [
        ("county", "Training counties"),
        ("role", "Participant roles"),
        ("language", "Survey languages"),
    ]:
        st.markdown(f"#### {title}")
        coverage = summary["coverage"][field]
        groups = sorted(coverage["groups"], key=lambda item: item["n"], reverse=True)[:15]
        if not groups:
            st.info("No answered categories in this selection.")
            continue
        fig = _bar(
            groups, "category", "n", x_title="Survey responses",
            color=JADE, horizontal=True,
        )
        fig.update_layout(showlegend=False)
        label_width = min(290, max(165, max(len(str(x["category"])) for x in groups)*7 + 30))
        _chart(fig, f"representation_{field}",
               height=max(285, 42*len(groups)+105), left=label_width)
        st.caption(
            f"{coverage['missing_category_n']:,} respondents left this category blank. "
            + ("Roles can overlap when respondents selected several." if field == "role" else "")
        )
        st.divider()
    dates = summary["coverage"]["training_date"]
    if dates["dates"]:
        st.markdown("#### Responses by training date")
        fig = go.Figure(go.Bar(
            x=[v["date"][:10] for v in dates["dates"]],
            y=[v["n"] for v in dates["dates"]],
            marker_color=JADE,
        ))
        fig.update_xaxes(title="Reported training date", type="category")
        fig.update_yaxes(title="Survey responses", rangemode="tozero")
        _chart(fig, "training_dates", height=350)
        st.caption(f"{dates['missing_or_invalid_n']:,} missing/invalid dates.")
    st.caption(
        "County is training affiliation, not residence. Differences in response "
        "counts do not establish population differences."
    )


def render_missingness(summary):
    st.subheader("Answer coverage")
    records = summary["missingness"]
    fig = go.Figure()
    labels = [LABELS.get(r["field"], r["field"]) for r in records]
    for label, key, color in [("Unanswered", "source_missing_n", MUTED), ("Invalid / unusable", "invalid_or_unusable_n", UMBER)]:
        fig.add_bar(name=label, y=labels, x=[r[key] for r in records], orientation="h", marker_color=color)
    fig.update_layout(barmode="stack", height=650)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Rows without usable answers", rangemode="tozero")
    _chart(fig, "missingness", height=720, left=260)
    st.caption(f"Question: completeness of each field. Counts across {summary['overview']['survey_rows']} selected rows; source blanks and unusable answers are separate. Nonresponse does not establish unwillingness or explain its cause.")
    st.dataframe(pd.DataFrame(records).assign(question=labels)[["question", "source_missing_n", "invalid_or_unusable_n", "usable_n", "denominator_rows"]], hide_index=True, width="stretch")
    st.markdown("**Willingness answer coverage by group**")
    group_field = st.selectbox("Group coverage by", ["county", "role", "language"], key="coverage_group")
    records = summary["coverage"][group_field]["groups"]
    if records:
        table = pd.DataFrame(records)[["category", "n", "willingness_valid_n", "willingness_missing_or_invalid_n", "willingness_response_rate", "small_group"]]
        table["willingness_response_rate"] = table["willingness_response_rate"].map(percent)
        st.dataframe(table, hide_index=True, width="stretch")
    st.caption(f"Denominator is each group's n. Small-group flag: n < {summary['min_group_n']}. Role groups overlap; coverage differences do not establish causes.")


def render_comparisons(summary):
    st.subheader("Comparison explorer")
    field = st.selectbox("Compare knowledge by", ["county", "role", "language"], key="comparison_group")
    topic = st.selectbox("Knowledge topic", list(summary["knowledge"]["topics"]), key="comparison_topic")
    rows = []
    for group in summary["group_comparisons"][field]:
        stats = group["knowledge"]["topics"][topic]
        rows.append({"group": group["category"], "group_rows": group["n"],
                     "paired_n": stats["n"], "incomplete_pairs": stats["missing_pair_rows"],
                     "before_mean": stats["before_mean"], "after_mean": stats["after_mean"],
                     "mean_change": stats["mean_change"],
                     "status": "Suppressed: small paired sample" if stats["suppressed"] else "Descriptive comparison"})
    if not rows:
        st.info("No answered group categories to compare.")
        return
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    visible = [row for row in rows if row["mean_change"] is not None]
    if visible:
        fig = _bar(visible, "group", "mean_change", x_title="Paired mean change (points)")
        fig.update_yaxes(range=[-4, 4], zeroline=True)
        _chart(fig, "comparison_chart")
    st.caption(f"Question: {topic}. Valid matched n and incomplete pairs shown per group. Comparisons with paired n < {summary['min_group_n']} are suppressed. Alphabetical groups, not ranked. {TOPIC_LIMIT} Role groups overlap; differences may reflect who responded.")


def render_quality(quality):
    """Full-source audit, explicitly separate from filtered dashboard results."""
    with st.expander("Data-quality report · full source before filters"):
        st.write(f"Source rows: **{quality['original_row_count']:,}** · Distinct IDs: **{quality['distinct_nonmissing_ids']:,}**")
        st.write("Duplicate ID checks:", quality["duplicate_ids"])
        st.write("Invalid or nonstandard ratings:", quality["invalid_values"])
        st.write("Unmapped categories:", quality["unmapped_categories"])
        st.write("Date parsing failures:", quality["date_failures"])
        st.write("Normalization counts:", quality["normalization_counts"])
        st.write("Training date range:", quality["training_date_range"])
        st.dataframe(pd.DataFrame.from_dict(quality["missingness"], orient="index"), width="stretch")
        st.caption("Missingness above uses the complete source; the Answer coverage tab uses your current selection. Invalid values are excluded from scored calculations; no ratings are imputed.")


def render_dashboard(clean_df, summary):
    if clean_df.empty:
        st.info("No survey rows match these filters. Change your filters in the sidebar to see more.")
        return

    render_overview(summary)

    # All original views remain available, but are no longer crowded onto
    # the first screen. This is a display change only; no feature was deleted.
    with st.expander("Explore detailed charts", expanded=False):
        tabs = st.tabs([
            "Knowledge",
            "Training experience",
            "Representation",
            "Answer coverage",
            "Compare groups",
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
