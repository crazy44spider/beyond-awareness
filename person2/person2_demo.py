import streamlit as st
import pandas as pd

from pathlib import Path
from sample_data import create_sample_data

from gap_detector import (
    knowledge_summary,
    willingness_summary,
    knowledge_vs_willingness,
    subgroup_summary,
    detect_findings
)


# Page setup
st.set_page_config(
    page_title="988 Survey Analysis",
    page_icon="📊",
    layout="wide"
)

# Load cleaned survey data
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "cleaned_survey.csv"

if not DATA_PATH.exists():
    st.error(
        "Cleaned survey data not found. "
        "Please run cleaning.py first."
    )
    st.stop()

df = pd.read_csv(DATA_PATH)
st.success(f"Using {len(df):,} actual survey responses.")

# Dashboard title
st.title("988 Survey Analysis Dashboard")

st.write(
    "Explore knowledge changes, willingness to call 988, "
    "subgroup differences, and evidence-based findings."
)

# Calculate summary statistics
knowledge = knowledge_summary(df)
willingness = willingness_summary(df)
comparison = knowledge_vs_willingness(df)


# Summary metrics
st.subheader("Survey Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Responses", willingness["total_responses"])

with col2:
    paired_counts = " / ".join(
        str(n) for n in knowledge["paired_n"]
    )

with col3:
    st.metric("Willingness Answers", willingness["answered"])

with col4:
    st.metric(
        "Willingness Response Rate",
        f"{willingness['response_rate']:.1f}%"
    )


# Dashboard tabs
learning_tab, action_tab, equity_tab, findings_tab = st.tabs([
    "Learning",
    "Knowledge vs. Action",
    "Equity Lens",
    "Evidence Feed"
])


with learning_tab:
    st.header("Learning")

    st.write(
        "Compare participants' recalled-before knowledge "
        "with their current knowledge ratings."
    )

    st.caption(
        "Ratings are retrospective self-reports, not prospective "
        "pre/post measurements."
    )

    display_knowledge = knowledge[
        [
            "label",
            "recalled_before_mean",
            "current_mean",
            "mean_difference",
            "increased",
            "unchanged",
            "decreased"
        ]
    ].copy()

    display_knowledge.columns = [
        "Topic",
        "Recalled Before Mean",
        "Current Mean",
        "Mean Difference",
        "Increased",
        "Unchanged",
        "Decreased"
    ]

    st.table(display_knowledge.round(2))

with action_tab:
    st.header("Knowledge vs. Action")

    st.write(
        "Explore whether participants who report higher knowledge "
        "also report greater willingness to call 988."
    )

    st.metric(
        "Complete Responses",
        comparison["complete_case_n"]
    )

    st.metric(
        "Excluded Responses",
        comparison["excluded_n"]
    )

    st.subheader("Willingness by Knowledge Rating")

    st.dataframe(
        comparison["by_knowledge"].round(2),
        use_container_width=True
    )

    st.subheader("Knowledge and Willingness Distribution")

    st.caption(
        "The table shows participant counts for each combination "
        "of knowledge rating and willingness score."
    )

    st.dataframe(
        comparison["heatmap"],
        use_container_width=True
    )

    st.subheader("Exploratory Knowledge-Willingness Gap")

    st.write(
        f"{comparison['gap_count']} of "
        f"{comparison['complete_case_n']} complete cases "
        f"({comparison['gap_percentage']:.1f}%) had knowledge "
        "ratings of 4–5 and willingness scores of 0–5."
    )

    st.caption(
        "This is an exploratory descriptive definition, not a "
        "validated clinical cutoff."
    )

with equity_tab:
    st.header("Equity Lens")

    st.write(
        "Compare knowledge and willingness across counties."
    )

    subgroup_data = subgroup_summary(df, "county")

    st.subheader("Results by County")

    st.dataframe(
        subgroup_data.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Groups with fewer than 20 participants are labeled "
        "descriptive only. County represents training affiliation, "
        "not verified participant residence."
    )

with findings_tab:
    st.header("Evidence Feed")

    st.write(
        "Automatically detected patterns supported by the survey data."
    )

    findings = detect_findings(df)

    for finding in findings:
        with st.expander(finding["title"]):
            st.write("**Evidence:**")
            st.write(finding["evidence"])

            st.write("**Limitations:**")
            st.write(finding["limitation"])