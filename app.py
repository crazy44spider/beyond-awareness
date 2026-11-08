
import streamlit as st

st.set_page_config(
    page_title="Beyond Awareness",
    page_icon="🧠",
    layout="wide"
)

st.title("Beyond Awareness")
st.caption("988 Training Evaluation & Improvement Platform")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose a tool",
    [
        "Dashboard",
        "Gap Detector",
        "Feedback Analyzer",
        "Survey Designer",
        "Intervention Planner",
        "Report Generator"
    ]
)

st.header(page)

st.info(f"The {page} module is under development.")
