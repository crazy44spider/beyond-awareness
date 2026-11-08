import pandas as pd
import streamlit as st

from survey_designer import analyze_survey, render_survey_designer

st.set_page_config(
    page_title="EveryMind — Survey Designer",
    page_icon="📋",
    layout="wide"
)

st.title("EveryMind 988 Training Improvement")

uploaded_file = st.file_uploader(
    "Upload an EveryMind survey",
    type=["xlsx"]
)

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    report = analyze_survey(df)

    render_survey_designer(report)
else:
    st.info("Upload a survey spreadsheet to begin.")