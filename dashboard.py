from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PURPLE = "#8064B3"
TEAL = "#148A83"
AMBER = "#A96509"
GRAY = "#64748B"
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
    """Keep native theme colors so browser dark/light preferences stay readable."""
    st.markdown("""<style>
    [data-testid="stMetric"] {border: 1px solid rgba(128, 128, 128, 0.35);
       border-radius: 14px; padding: 16px;}
    .stTabs [data-baseweb="tab"] {font-weight: 600;}
    </style>""", unsafe_allow_html=True)


def _chart(fig, key, *, percent_axis=False, height=330):
    fig.update_layout(
        template=None, font=dict(family="Arial, sans-serif", size=14),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=12, r=12, t=24, b=12),
        legend=dict(orientation="h", y=1.16, x=0),
        height=height, hovermode="closest",
    )
    if percent_axis:
        fig.update_yaxes(range=[0, 100], title="Share of valid paired responses (%)")
    st.plotly_chart(fig, width="stretch", theme="streamlit", key=key, config={"displaylogo": False})


def _bar(records, category, value, *, x_title, color=PURPLE, horizontal=False):
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
    overview = summary["overview"]
    cols = st.columns(3)
    for col, label, value in zip(cols, ["Survey rows", "Training dates", "Fully paired knowledge rows"],
                                 [overview["survey_rows"], overview["distinct_training_dates"], overview["fully_paired_knowledge_rows"]]):
        col.metric(label, f"{value:,}")
    cols = st.columns(3)
    cols[0].metric("Willingness answer coverage", percent(overview["willingness_response_rate"]))
    cols[1].metric("Training counties", overview["county_count"])
    cols[2].metric("Role categories", overview["role_category_count"])
    st.caption(
        f"All cards use the current selection: {overview['survey_rows']:,} rows. "
        f"Willingness: {overview['willingness_valid_n']:,} valid answers; "
        f"{overview['willingness_missing_or_invalid_n']:,} missing or invalid. "
        "Survey rows and distinct IDs do not establish unique individuals."
    )
    st.subheader("Reported knowledge, before and after")
    records = summary["knowledge"]["topics"]
    fig = go.Figure()
    for label, field, color in [("Recalled before", "before_mean", PURPLE), ("Current", "after_mean", TEAL)]:
        fig.add_bar(name=label, x=list(records), y=[v[field] for v in records.values()], marker_color=color)
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, 5], title="Mean coded agreement (1–5)")
    _chart(fig, "overview_knowledge")
    sample_text = "; ".join(f"{topic}: n={s['n']}, incomplete={s['missing_pair_rows']}" for topic, s in records.items())
    st.caption(f"Question: perceived knowledge in each topic. Matched answers per topic. {sample_text}. {TOPIC_LIMIT}")
    if overview["survey_rows"] < summary["min_group_n"]:
        st.warning(f"This selection contains fewer than {summary['min_group_n']} rows. Treat descriptive results with caution.")
    st.info("Representation & measurement: this survey describes who responded. It does not measure population need or prove who faces barriers to using 988.")


def render_knowledge(summary):
    st.subheader("Knowledge distributions")
    st.caption("1 Strongly disagree · 2 Disagree · 3 Neutral · 4 Agree · 5 Strongly agree")
    columns = st.columns(3)
    for i, (topic, stats) in enumerate(summary["knowledge"]["topics"].items()):
        with columns[i]:
            st.markdown(f"**{topic}**")
            paired = summary["distributions"]["knowledge_paired"][topic]
            fig = go.Figure()
            for period, label, color in [("before", "Recalled before", PURPLE), ("after", "Current", TEAL)]:
                fig.add_bar(name=label, x=[r["value"] for r in paired[period]["values"]],
                            y=[None if r["share"] is None else r["share"] * 100 for r in paired[period]["values"]], marker_color=color)
            fig.update_layout(barmode="group")
            fig.update_xaxes(title="Agreement score", dtick=1)
            _chart(fig, f"knowledge_{i}", percent_axis=True)
            st.metric("Paired mean change", number(stats["mean_change"], signed=True))
            st.caption(f"n={stats['n']} of {stats['denominator_rows']} rows; {stats['missing_pair_rows']} incomplete pairs. {TOPIC_LIMIT}")
            st.write(f"Higher: **{percent(stats['share_up'])}** · Same: **{percent(stats['share_same'])}** · Lower: **{percent(stats['share_down'])}**")
    overall = summary["knowledge"]["overall_three_topic_mean"]
    st.subheader("Overall three-topic average")
    st.write(f"Recalled before: **{number(overall['before_mean'])}** → Current: **{number(overall['after_mean'])}** · Change: **{number(overall['mean_change'], signed=True)}**")
    st.caption(f"n={overall['n']} rows with all six answers; {overall['missing_pair_rows']} excluded. Equal-weight row averages, not a validated composite scale. {TOPIC_LIMIT}")


def _rating_chart(dist, key, label, scale_max):
    _chart(_bar(dist["values"], "value", "count", x_title="Valid answers", color=TEAL), key)
    st.caption(f"Question: {label}. Scale 0–{scale_max}. Counts among {dist['valid_n']} valid answers out of {dist['denominator_rows']} rows; {dist['missing_or_invalid_n']} missing/invalid. Self-reported intention does not establish behavior.")


def render_experience(clean_df, summary):
    st.subheader("Training experience")
    cols = st.columns(3)
    for i, (field, dist) in enumerate(summary["distributions"]["training_experience"].items()):
        with cols[i]:
            st.markdown(f"**{LABELS[field]}**")
            _chart(_bar(dist["values"], "value", "count", x_title="Valid answers"), f"experience_{i}")
            invalid = int(clean_df[f"{field}_invalid"].sum())
            st.caption(f"Agreement 1–5: {dist['valid_n']} valid of {dist['denominator_rows']} rows; {dist['missing_or_invalid_n']} missing/invalid. Ordinal self-report.")
            if invalid:
                st.warning(f"{invalid} nonstandard answers excluded from scoring.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Recommend training**")
        _rating_chart(summary["distributions"]["recommend_training"], "recommend", "Likelihood of recommending training", 10)
    with right:
        st.markdown("**Willingness to call 988**")
        _rating_chart(summary["distributions"]["willingness_to_call"], "willingness", "Likelihood of calling 988", 10)


def render_representation(summary):
    st.subheader("Participation & representation")
    cols = st.columns(3)
    for col, field, title in zip(cols, ["county", "role", "language"], ["Training counties", "Role selections", "Survey languages"]):
        with col:
            st.markdown(f"**{title}**")
            coverage = summary["coverage"][field]
            if coverage["groups"]:
                _chart(_bar(coverage["groups"], "category", "n", x_title="Survey rows", horizontal=True), f"representation_{field}")
            else:
                st.info("No answered categories in this selection.")
            st.caption(f"Counts from {summary['overview']['survey_rows']} selected rows; {coverage['missing_category_n']} unanswered categories. " + ("Multi-select roles overlap." if field == "role" else "Response share does not establish population coverage."))
    dates = summary["coverage"]["training_date"]
    if dates["dates"]:
        fig = go.Figure(go.Bar(x=[v["date"][:10] for v in dates["dates"]], y=[v["n"] for v in dates["dates"]], marker_color=TEAL))
        fig.update_xaxes(title="Reported training date", type="date")
        fig.update_yaxes(title="Survey rows", rangemode="tozero")
        _chart(fig, "training_dates")
        st.caption(f"Reported training dates for {sum(v['n'] for v in dates['dates'])} of {dates['denominator_rows']} rows; {dates['missing_or_invalid_n']} missing/invalid. Survey response volume does not measure attendance or training availability.")
    st.markdown("**Not measured by this survey**")
    st.write(" · ".join(UNMEASURED_BARRIERS))
    st.caption("These are candidate measurement gaps, not observed disparities. Do not infer race, income, immigration status, or mental health from geography.")


def render_missingness(summary):
    st.subheader("Answer coverage")
    records = summary["missingness"]
    fig = go.Figure()
    labels = [LABELS.get(r["field"], r["field"]) for r in records]
    for label, key, color in [("Unanswered", "source_missing_n", GRAY), ("Invalid / unusable", "invalid_or_unusable_n", AMBER)]:
        fig.add_bar(name=label, y=labels, x=[r[key] for r in records], orientation="h", marker_color=color)
    fig.update_layout(barmode="stack", height=650)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Rows without usable answers", rangemode="tozero")
    _chart(fig, "missingness", height=720)
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
        st.info("No survey rows match these filters. Clear a filter in the sidebar to continue.")
        return
    tabs = st.tabs(["Summary", "Knowledge", "Training experience", "Representation", "Answer coverage", "Compare groups"])
    with tabs[0]: render_overview(summary)
    with tabs[1]: render_knowledge(summary)
    with tabs[2]: render_experience(clean_df, summary)
    with tabs[3]: render_representation(summary)
    with tabs[4]: render_missingness(summary)
    with tabs[5]: render_comparisons(summary)
