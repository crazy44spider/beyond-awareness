from pathlib import Path
import pandas as pd
import re

# Find the main project folder, regardless of where Python is run
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Locate Person 1's cleaned dataset
DATA_PATH = PROJECT_ROOT / "survey_data.xlsx"
# Proposed questions for future surveys
question_bank = [
    # Cultural
    {
        "id": "CUL01",
        "dimension": "Cultural & Linguistic",
        "question": "How acceptable is seeking outside mental health support considered in your family or community?",
        "type": "Single choice",
        "options": [
            "Not at all acceptable",
            "Slightly acceptable",
            "Moderately acceptable",
            "Very acceptable",
            "Extremely acceptable",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure perceived community attitudes toward seeking "
            "mental health support, including potential stigma."
        )
    },

    {
        "id": "CUL02",
        "dimension": "Cultural & Linguistic",
        "question": "How well did the training address differences in cultural beliefs, family expectations, or language needs?",
        "type": "Single choice",
        "options": [
            "Not at all well",
            "Slightly well",
            "Moderately well",
            "Very well",
            "Extremely well",
            "These topics were not addressed",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Evaluate whether training addresses cultural, "
            "intergenerational, and linguistic differences."
        )
    },

    # Socioeconomic/Practical Access
    {
        "id": "PRA01",
        "dimension": "Socioeconomic & Practical",
        "question": "Which practical circumstances, if any, could make it difficult for you to access 988?",
        "type": "Multiple choice (select all)",
        "options": [
            "Limited access to a phone or internet",
            "Lack of a private space",
            "Limited time or caregiving responsibilities",
            "Disability-related access needs",
            "Other practical circumstances",
            "None of these",
            "Prefer not to answer"
        ],
        "purpose": (
            "Identify practical barriers that may affect access "
            "even when someone knows about 988."
        )
    },

    {
        "id": "PRA02",
        "dimension": "Socioeconomic & Practical",
        "question": "Before this training, did you know that 988 provides free crisis support without requiring transportation or health insurance?",
        "type": "Single choice",
        "options": [
            "Yes, I knew all of this",
            "I knew some of this",
            "No, I did not know this",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure prior awareness of 988's practical "
            "accessibility and cost-related advantages."
        )
    },

    # Communication 

    {
        "id": "COM01",
        "dimension": "Communication",
        "question": "Which method of contacting 988 would you feel most comfortable using, and why?",
        "type": "Single choice + optional explanation",
        "options": [
            "Phone call",
            "Text message",
            "Online chat",
            "I would feel equally comfortable with multiple methods",
            "I would not feel comfortable with any method",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Identify communication preferences beyond calling, "
            "which is the only method covered by the current "
            "survey's willingness question."
        )
    },

    {
        "id": "COM02",
        "dimension": "Communication",
        "question": "How confident are you that you could communicate effectively with 988 using your preferred language or communication needs?",
        "type": "Single choice",
        "options": [
            "Not at all confident",
            "Slightly confident",
            "Moderately confident",
            "Very confident",
            "Extremely confident",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure perceived language and communication "
            "accessibility, including disability-related needs."
        )
    },

    # Institutional Trust
    {
        "id": "TRU01",
        "dimension": "Institutional Trust",
        "question": "How clearly did the training explain 988's confidentiality practices and when emergency services might become involved?",
        "type": "Single choice",
        "options": [
            "Not at all clearly",
            "Slightly clearly",
            "Moderately clearly",
            "Very clearly",
            "Extremely clearly",
            "These topics were not explained",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Evaluate whether training explains privacy and "
            "emergency response policies clearly."
        )
    },

    {
        "id": "TRU02",
        "dimension": "Institutional Trust",
        "question": "How much would you trust a 988 counselor to listen respectfully and take your concerns seriously?",
        "type": "Single choice",
        "options": [
            "Not at all",
            "A little",
            "Moderately",
            "A lot",
            "Completely",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure anticipated trust in 988 counselors, "
            "separately from understanding confidentiality policies."
        )
    },

    # Psychological

    {
        "id": "PSY01",
        "dimension": "Psychological",
        "question": "How confident are you that you could recognize when your own experiences are serious enough to seek support from 988?",
        "type": "Single choice",
        "options": [
            "Not at all confident",
            "Slightly confident",
            "Moderately confident",
            "Very confident",
            "Extremely confident",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure whether participants recognize that 988 "
            "can support people beyond suicidal emergencies."
        )
    },

    {
        "id": "PSY02",
        "dimension": "Psychological",
        "question": "How comfortable would you feel discussing a painful or personal experience with a 988 counselor?",
        "type": "Single choice",
        "options": [
            "Not at all comfortable",
            "Slightly comfortable",
            "Moderately comfortable",
            "Very comfortable",
            "Extremely comfortable",
            "Not sure",
            "Prefer not to answer"
        ],
        "purpose": (
            "Measure emotional comfort with disclosing personal "
            "experiences, separately from knowing when to seek help."
        )
    }
]
# Mapping detected survey gaps to questions that'd answer em
finding_rules = {
    "low_call_intent_response_rate": ["COM01"],
    "cultural_relevance_concern": ["CUL02"],
    "community_stigma_concern": ["CUL01"],
    "practical_access_concern": ["PRA01"],
    "cost_awareness_gap": ["PRA02"],
    "communication_access_concern": ["COM02"],
    "privacy_policy_confusion": ["TRU01"],
    "counselor_trust_concern": ["TRU02"],
    "crisis_eligibility_confusion": ["PSY01"],
    "disclosure_discomfort": ["PSY02"]
}

# ============================================================
# PART 4A: CONNECT FINDINGS TO QUESTIONS
# ============================================================

# These are additional findings YOUR code can detect.
# Your earlier finding_rules dictionary stays exactly as it is.

finding_rules.update({
    "call_only_measure": ["COM01"],
    "privacy_information_request": ["TRU01"],
    "language_access_request": ["COM02"]
})


# ============================================================
# PART 4B: RECOGNIZE SURVEY COLUMNS
# ============================================================

# Person 1 might rename columns later.
# This lets us handle the original Excel survey AND several
# shorter column names used by the team.

COLUMN_ALIASES = {
    "willingness_to_call": [
        "willingness_to_call",
        "likely_call",
        "how likely are you to call 988"
    ],

    "valuable_feedback": [
        "valuable_feedback",
        "learned_en",
        "learned_clean",
        "learned",
        "what was the most valuable thing you learned"
    ],

    "improvement_feedback": [
        "improvement_feedback",
        "improve_en",
        "improve_clean",
        "improve",
        "how can we improve this training"
    ]
}


def normalize_header(value):
    """Make column names easier to compare."""
    return " ".join(
        re.findall(r"[a-z0-9]+", str(value).lower())
    )


def standardize_survey(df):
    """
    Take a DataFrame and give its important columns
    consistent names WITHOUT modifying the original.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "Please pass a pandas DataFrame."
        )

    data = df.copy()

    headers = [
        (name, normalize_header(name))
        for name in data.columns
    ]

    for standard_name, aliases in COLUMN_ALIASES.items():

        # Already has the correct column name!
        if standard_name in data.columns:
            continue

        matching_column = None

        for alias in aliases:
            normalized_alias = normalize_header(alias)

            for original_name, normalized_name in headers:

                exact_match = (
                    normalized_name == normalized_alias
                )

                partial_match = (
                    len(normalized_alias) > 15
                    and normalized_alias in normalized_name
                )

                if exact_match or partial_match:
                    matching_column = original_name
                    break

            if matching_column is not None:
                break

        if matching_column is None:
            raise ValueError(
                f"Could not find '{standard_name}'. "
                "Please use the existing EveryMind survey format "
                "or Person 1's compatible cleaned data."
            )

        data[standard_name] = data[matching_column]

    return data


# ============================================================
# PART 4C: ACCESSIBILITY COVERAGE AUDIT
# ============================================================

def coverage_audit(data):
    """
    Identify important accessibility topics the survey
    currently measures, partly measures, or does not
    directly measure.

    IMPORTANT: This checks the SURVEY DESIGN.
    It does NOT assume that respondents have barriers.
    """

    has_language = any(
        normalize_header(col) in {
            "language",
            "survey language"
        }
        for col in data.columns
    )

    cultural_status = (
        "Partially measured"
        if has_language
        else "Not directly measured"
    )

    rows = [
        {
            "dimension": "Cultural & Linguistic",
            "coverage": cultural_status,
            "explanation": (
                "Survey language may be recorded, but "
                "community stigma and cultural fit are "
                "not directly assessed."
            )
        },

        {
            "dimension": "Socioeconomic & Practical",
            "coverage": "Not directly measured",
            "explanation": (
                "No direct question about practical barriers "
                "such as phone access, internet, privacy, "
                "time, or caregiving responsibilities."
            )
        },

        {
            "dimension": "Communication",
            "coverage": "Partially measured",
            "explanation": (
                "The survey asks about willingness to CALL "
                "988, but not preferences for text or chat."
            )
        },

        {
            "dimension": "Institutional Trust",
            "coverage": "Not directly measured",
            "explanation": (
                "No direct rating of trust in counselors "
                "or understanding confidentiality practices."
            )
        },

        {
            "dimension": "Psychological",
            "coverage": "Not directly measured",
            "explanation": (
                "No direct question about emotional comfort "
                "or whether someone feels their experiences "
                "are serious enough to seek support."
            )
        }
    ]

    return pd.DataFrame(rows)


# ============================================================
# PART 4D: HELPER FOR CREATING FINDINGS
# ============================================================

def make_finding(
    finding_type,
    title,
    description,
    source,
    count=None,
    denominator=None,
    limitations=None,
    evidence=None
):
    """
    Create a finding in the format our team can share.
    """

    percentage = None

    if count is not None and denominator:
        percentage = round(
            count / denominator * 100,
            1
        )

    return {
        "id": finding_type,
        "source": source,
        "type": finding_type,
        "title": title,
        "description": description,
        "count": count,
        "denominator": denominator,
        "percentage": percentage,
        "limitations": limitations or [],
        "evidence": evidence or {}
    }


# ============================================================
# PART 4E: ACTUALLY DETECT FINDINGS
# ============================================================

def detect_findings(data, missingness_threshold=30):
    """
    Analyze the actual uploaded survey.

    The 30% threshold is only a customizable alert
    setting, NOT a scientific cutoff.
    """

    findings = []
    total = len(data)

    # --------------------------------------------------------
    # FINDING 1: The survey only asks about calling
    # --------------------------------------------------------

    findings.append(
        make_finding(
            finding_type="call_only_measure",
            title=(
                "The survey asks about calling, "
                "but not texting or chatting"
            ),
            description=(
                "The current willingness question only "
                "measures willingness to CALL 988."
            ),
            source="accessibility_audit",
            limitations=[
                "This does not tell us which method "
                "participants actually prefer."
            ],
            evidence={
                "column": "willingness_to_call"
            }
        )
    )

    # --------------------------------------------------------
    # FINDING 2: Missing willingness-to-call responses
    # --------------------------------------------------------

    answers = (
        data["willingness_to_call"]
        .astype("string")
        .str.strip()
    )

    answered_mask = (
        answers.notna() & (answers != "")
    ).fillna(False)

    answered_count = int(answered_mask.sum())

    missing_count = total - answered_count

    if total > 0:
        missing_percent = missing_count / total * 100
    else:
        missing_percent = 0

    if total > 0 and missing_percent >= missingness_threshold:

        findings.append(
            make_finding(
                finding_type="low_call_intent_response_rate",

                title=(
                    f"{missing_percent:.1f}% of willingness-"
                    "to-call responses are missing"
                ),

                description=(
                    f"{missing_count:,} of {total:,} "
                    "respondents did not provide an answer "
                    "to this question."
                ),

                source="accessibility_audit",

                count=missing_count,
                denominator=total,

                limitations=[
                    "Missing does not mean unwilling.",
                    "We do not know whether every "
                    "respondent saw this question.",
                    "The alert threshold is a design "
                    "choice, not a scientific cutoff."
                ],

                evidence={
                    "column": "willingness_to_call",
                    "answered": answered_count
                }
            )
        )

    # --------------------------------------------------------
    # FINDINGS 3 & 4: Look for privacy/language topics
    # inside written improvement feedback.
    #
    # This is a SIMPLE keyword screen, not Person 3's
    # full thematic analysis.
    # --------------------------------------------------------

    comments = (
        data["improvement_feedback"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    nonanswers = {
        "na",
        "n/a",
        "none",
        "nothing",
        "no",
        "nope",
        "no comment",
        "not applicable"
    }

    valid_comments = (
        (comments != "")
        & ~comments.str.lower().isin(nonanswers)
    )

    number_of_comments = int(valid_comments.sum())

    # We will check two specific topics.
    #
    # Each tuple contains:
    # 1. finding type
    # 2. finding title
    # 3. regex pattern to search
    # 4. explanation

    signals = [
        (
            "privacy_information_request",

            "Privacy-related topics appeared "
            "in improvement comments",

            r"\b(?:privacy|private|confidential\w*|"
            r"police|anonymous|recorded|recording|"
            r"emergency services)\b",

            "Follow-up questions could check how clearly "
            "the training explained confidentiality "
            "and emergency involvement."
        ),

        (
            "language_access_request",

            "Language-related topics appeared "
            "in improvement comments",

            r"\b(?:spanish|translator\w*|translat\w*|"
            r"interpret\w*|bilingual|other languages)\b",

            "Follow-up questions could measure confidence "
            "in language and communication accessibility."
        )
    ]

    for finding_type, title, pattern, description in signals:

        matches = (
            valid_comments
            & comments.str.contains(
                pattern,
                case=False,
                regex=True,
                na=False
            )
        )

        count = int(matches.sum())

        if count == 0:
            continue

        findings.append(
            make_finding(
                finding_type=finding_type,
                title=title,
                description=description,
                source="keyword_screening",
                count=count,
                denominator=number_of_comments,

                limitations=[
                    "Keyword matching is approximate.",
                    "A keyword mention is not proof "
                    "of confusion or concern.",
                    "Some Spanish-language comments "
                    "may be missed without translation.",
                    "Comments should be manually reviewed."
                ],

                evidence={
                    "column": "improvement_feedback",
                    "method": "keyword matching"
                }
            )
        )

    # Give summary statistics back as well.

    summary = {
        "total_responses": total,
        "answered_call_item": answered_count,
        "missing_call_item": missing_count,
        "missing_call_percent": round(
            missing_percent, 1
        ),
        "nonempty_improvement_comments": number_of_comments
    }

    return findings, summary


# ============================================================
# PART 4F: ACCEPT TEAMMATES' FINDINGS
# ============================================================

def prepare_external_findings(external_findings):
    """
    Person 2 or 3 can send us findings later.

    They can provide:
      - a list of dictionaries
      - a pandas DataFrame
      - a dictionary containing a 'findings' list
    """

    if external_findings is None:
        return []

    if isinstance(external_findings, dict):
        external_findings = external_findings.get(
            "findings",
            []
        )

    if isinstance(external_findings, pd.DataFrame):
        external_findings = external_findings.to_dict(
            "records"
        )

    if not isinstance(external_findings, (list, tuple)):
        raise TypeError(
            "External findings must be a list of dictionaries."
        )

    for finding in external_findings:

        if not isinstance(finding, dict):
            raise ValueError(
                "Each finding must be a dictionary."
            )

        if not finding.get("type"):
            raise ValueError(
                "Each finding needs a 'type' field."
            )

    return list(external_findings)


# ============================================================
# PART 4G: RECOMMEND QUESTIONS BASED ON FINDINGS
# ============================================================

def recommend_questions(findings):
    """
    Go through the findings and find matching questions
    using your existing finding_rules.

    Do not recommend the same question twice.
    """

    question_lookup = {
        q["id"]: q
        for q in question_bank
    }

    recommendations = {}

    for finding in findings:

        finding_type = finding["type"]

        matched_ids = finding_rules.get(
            finding_type,
            []
        )

        for question_id in matched_ids:

            if question_id not in question_lookup:
                continue

            question = question_lookup[question_id]

            if question_id not in recommendations:

                recommendations[question_id] = {
                    "question_id": question_id,
                    "dimension": question["dimension"],
                    "question": question["question"],
                    "response_type": question["type"],
                    "options": question["options"],
                    "purpose": question["purpose"],
                    "why_recommended": [],
                    "evidence_sources": []
                }

            row = recommendations[question_id]

            title = finding["title"]
            source = finding["source"]

            if title not in row["why_recommended"]:
                row["why_recommended"].append(title)

            if source not in row["evidence_sources"]:
                row["evidence_sources"].append(source)

    # Convert recommendations to a DataFrame.

    columns = [
        "question_id",
        "dimension",
        "question",
        "response_type",
        "options",
        "purpose",
        "why_recommended",
        "evidence_sources"
    ]

    return pd.DataFrame(
        list(recommendations.values()),
        columns=columns
    )


# ============================================================
# PART 4H: MAIN FUNCTION FOR THE DASHBOARD
# ============================================================

def analyze_survey(df, external_findings=None):
    """
    THIS IS THE MAIN FUNCTION OTHER TEAMMATES WILL CALL.

    Input: a DataFrame from an uploaded Excel file.

    Output:
      - summary statistics
      - coverage audit
      - detected findings
      - recommended questions
      - full question bank
    """

    data = standardize_survey(df)

    automatic_findings, summary = detect_findings(data)

    # Store findings by type to avoid duplicates.
    findings_by_type = {
        finding["type"]: finding
        for finding in automatic_findings
    }

    # Add findings from Persons 2 and 3, if available.
    #
    # If the same type appears, use the team's result
    # instead of our basic automated result.

    team_findings = prepare_external_findings(
        external_findings
    )

    for finding in team_findings:
        findings_by_type[finding["type"]] = finding

    combined_findings = list(
        findings_by_type.values()
    )

    recommendations = recommend_questions(
        combined_findings
    )

    return {
        "summary": summary,

        "coverage": coverage_audit(data),

        "findings": combined_findings,

        "recommendations": recommendations,

        "question_bank": pd.DataFrame(question_bank)
    }


# ============================================================
# PART 4I: EXPORT QUESTIONS TO A CSV FILE
# ============================================================

def export_selected_questions(selected_ids):
    """
    Create CSV data for the download button.

    This exports suggested QUESTIONS, not actual
    participants' private responses.
    """

    chosen = set(selected_ids)

    rows = []

    for question in question_bank:

        if question["id"] in chosen:

            rows.append({
                "id": question["id"],
                "dimension": question["dimension"],
                "question": question["question"],
                "type": question["type"],
                "options": " | ".join(
                    question["options"]
                ),
                "purpose": question["purpose"]
            })

    columns = [
        "id",
        "dimension",
        "question",
        "type",
        "options",
        "purpose"
    ]

    csv_text = pd.DataFrame(
        rows,
        columns=columns
    ).to_csv(index=False)

    return csv_text.encode("utf-8-sig")


# ============================================================
# PART 4J: STREAMLIT DASHBOARD SECTION
# ============================================================

def render_survey_designer(report):
    """
    The dashboard owner can call this function
    inside their Streamlit app.

    We import Streamlit INSIDE the function so the
    analysis can still be tested without launching
    the dashboard.
    """

    import streamlit as st

    st.header("Accessibility & Adaptive Survey Designer")

    st.caption(
        "Evaluate what the survey measures, identify "
        "potential gaps, and recommend follow-up questions."
    )

    summary = report["summary"]

    # Top statistics

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Survey responses",
            f"{summary['total_responses']:,}"
        )

    with col2:
        st.metric(
            "Call-intent answers missing",
            f"{summary['missing_call_percent']:.1f}%"
        )

    with col3:
        st.metric(
            "Suggested questions available",
            len(question_bank)
        )

    # Coverage audit

    st.subheader("Accessibility Coverage Audit")

    st.dataframe(
        report["coverage"],
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "Coverage describes the questions the survey asks. "
        "It does not establish whether participants have "
        "these accessibility barriers."
    )

    # Findings

    st.subheader("Findings From This Survey")

    for finding in report["findings"]:

        with st.expander(finding["title"]):

            st.write(finding["description"])

            if finding.get("count") is not None:
                st.write(
                    f"Matched: {finding['count']} "
                    f"of {finding.get('denominator', '?')}"
                )

            st.caption(
                f"Source: {finding['source']}"
            )

            if finding.get("limitations"):

                st.write("**Limitations:**")

                for limitation in finding["limitations"]:
                    st.write(f"- {limitation}")

    # Recommended questions

    st.subheader("Recommended Follow-up Questions")

    recommendations = report["recommendations"]

    if recommendations.empty:
        st.info(
            "No rules produced a recommendation. "
            "You can still select questions from "
            "the full question bank below."
        )
    else:

        display = recommendations.copy()

        display["why_recommended"] = (
            display["why_recommended"].apply(
                lambda values: "; ".join(values)
            )
        )

        display["evidence_sources"] = (
            display["evidence_sources"].apply(
                lambda values: ", ".join(values)
            )
        )

        st.dataframe(
            display[[
                "question_id",
                "dimension",
                "question",
                "why_recommended",
                "evidence_sources"
            ]],
            hide_index=True,
            use_container_width=True
        )

    # Select and export questions

    st.subheader("Build a Follow-up Survey")

    st.write(
        "Choose which draft questions EveryMind "
        "should consider adding to a future survey."
    )

    question_lookup = {
        question["id"]: question
        for question in question_bank
    }

    recommended_ids = (
        recommendations["question_id"].tolist()
    )

    selected_ids = st.multiselect(
        "Select questions",
        options=list(question_lookup.keys()),
        default=recommended_ids,
        format_func=lambda question_id: (
            f"{question_id} — "
            f"{question_lookup[question_id]['question']}"
        )
    )

    if selected_ids:

        with st.expander("Preview selected questions"):

            for question_id in selected_ids:

                q = question_lookup[question_id]

                st.write(
                    f"**{question_id}: {q['question']}**"
                )

                st.caption(q["dimension"])

                for option in q["options"]:
                    st.write(f"- {option}")

                st.write(f"*Purpose:* {q['purpose']}")

    st.download_button(
        label="Download selected questions (CSV)",
        data=export_selected_questions(selected_ids),
        file_name="everymind_followup_questions.csv",
        mime="text/csv",
        disabled=(len(selected_ids) == 0)
    )

    st.caption(
        "These questions are proposals, not validated "
        "survey instruments. EveryMind should review "
        "wording, accessibility, and participant safety "
        "before using them."
    )


# ============================================================
# PART 4K: TEST YOUR PROGRAM DIRECTLY
# ============================================================

if __name__ == "__main__":

    if not DATA_PATH.exists():
        print(f"Survey file not found: {DATA_PATH}")

    else:
        # For now, use the original survey.
        # Later, the dashboard will supply uploaded data.

        original_df = pd.read_excel(DATA_PATH)

        report = analyze_survey(original_df)

        print("\n===== SURVEY SUMMARY =====")
        print(report["summary"])

        print("\n===== ACCESSIBILITY COVERAGE =====")
        print(
            report["coverage"].to_string(index=False)
        )

        print("\n===== DETECTED FINDINGS =====")

        for finding in report["findings"]:
            print("-", finding["title"])

        print("\n===== RECOMMENDED QUESTIONS =====")

        print(
            report["recommendations"][[
                "question_id",
                "question"
            ]].to_string(index=False)
        )