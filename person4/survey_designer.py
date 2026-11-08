from pathlib import Path
import pandas as pd
import re
from cleaning import EXPECTED_COLUMNS, SOURCE_HEADERS

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


# New, explicitly hypothesis-generating adapters. These rules suggest what
# to ask next, not what caused a knowledge/willingness difference.
finding_rules.update({
    "knowledge_willingness_gap": ["COM01", "TRU02", "PSY02"],
    "feedback_privacy_questions": ["TRU01"],
    "feedback_crisis_questions": ["PSY01"],
    "feedback_call_experience_questions": ["TRU02"],
    "feedback_local_relevance_questions": ["CUL02"],
})
# A lack of questions is evidence about the FORM, not evidence about people.
for _dimension, _ids in {
    "Cultural & Linguistic": ["CUL01", "CUL02"],
    "Socioeconomic & Practical": ["PRA01", "PRA02"],
    "Communication": ["COM01", "COM02"],
    "Institutional Trust": ["TRU01", "TRU02"],
    "Psychological": ["PSY01", "PSY02"],
}.items():
    for _id in _ids:
        finding_rules[f"questionnaire_missing_{_id.lower()}"] = [_id]


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

# The 10 original survey-question proposals are the source of truth for
# measurement dimensions. We inspect questionnaire HEADERS only: seeing a
# keyword in a participant's answer does not mean a question was asked.
_DIMENSION_QUESTIONS = {
    dimension: [q["id"] for q in question_bank if q["dimension"] == dimension]
    for dimension in dict.fromkeys(q["dimension"] for q in question_bank)
}

# Deliberately conservative signatures for paraphrased additions. Exact
# question_bank wording and explicit IDs are also supported. A classifier may
# miss a paraphrase; staff can inspect the recognized-question details.
_QUESTION_PATTERNS = {
    "CUL01": (r"\b(family|community|communities|stigma|cultural)\b",
              r"\b(acceptab|support|seek|seeking|mental health|attitude)"),
    "CUL02": (r"\b(training|presentation|session)\b",
              r"\b(cultur|family expectations|language needs|intergenerational)"),
    "PRA01": (r"\b(988|support|crisis|help)\b",
              r"\b(practical|barrier|difficult|prevent|limited|internet|private space|caregiv|transport|disabilit)"),
    "PRA02": (r"\b988\b",
              r"\b(cost|free|insurance|transportation)\b"),
    "COM01": (r"\b988\b",
              r"\b(text|texting|chat|messag|preferred method|contact method|ways of contacting)\b"),
    "COM02": (r"\b988\b",
              r"\b(language|interpret|asl|sign language|communication needs|communicat|accessib)"),
    "TRU01": (r"\b(988|training|presentation|crisis)\b",
              r"\b(confidential|privacy|police|emergency services|recording|anonymous|anonymity)"),
    "TRU02": (r"\b(988|counselor|counsellor)\b",
              r"\b(trust|respect|judg|listen|take.*serious)"),
    "PSY01": (r"\b(988|support|help)\b",
              r"\b(serious enough|own experience|my situation|need support|beyond suicid|not only suicid)"),
    "PSY02": (r"\b(988|counselor|counsellor|personal experience)\b",
              r"\b(comfortable|discuss|share|open up|talk about|personal|painful)"),
}

# These 20 mandatory survey fields measure some knowledge and response
# variables already. They should not be mistaken for NEW direct questions.
_CORE_HEADERS = {
    normalize_header(name)
    for name in (*EXPECTED_COLUMNS, *SOURCE_HEADERS)
}


def identify_direct_questions(data):
    """Return mapped question IDs and original column headers.

    Uses the question bank and transparent pattern rules; it does not use AI
    to infer a survey question from an individual's free-text response.
    """
    found = {qid: [] for ids in _DIMENSION_QUESTIONS.values() for qid in ids}
    supplements = []
    for column in data.columns:
        raw = str(column)
        normalized = normalize_header(raw)
        if normalized in _CORE_HEADERS or raw.endswith(("_raw", "_invalid")):
            continue
        if raw.startswith(("paired_",)) or raw in {
            "role_list", "duplicate_id", "county_unmapped", "role_unmapped",
            "language_unmapped", "paired_all_knowledge", "role_raw"
        }:
            continue
        if not normalized:
            continue
        supplements.append(raw)
        for question in question_bank:
            qid = question["id"]
            exact_wording = normalized == normalize_header(question["question"])
            explicit_id = bool(re.match(r"^" + qid.lower() + r"(?:\b|$)", raw.lower()))
            tests = _QUESTION_PATTERNS.get(qid, ())
            paraphrase = bool(tests) and all(re.search(p, normalized) for p in tests)
            if exact_wording or explicit_id or paraphrase:
                found[qid].append(raw)
    return {"by_id": found, "supplemental_columns": supplements,
            "recognized_columns": sorted({c for cols in found.values() for c in cols})}


def coverage_audit(data):
    """Re-evaluate questionnaire *design* after every new upload.

    "Directly measured" means at least one direct follow-up question is
    present, not that the full construct has been psychometrically validated.
    """
    mapped = identify_direct_questions(data)
    has_language = any(
        normalize_header(col) in {"language", "survey language"}
        for col in data.columns
    )
    has_call_intent = any(
        normalize_header(col) in {
            "willingness to call", "how likely are you to call 988",
        }
        for col in data.columns
    ) or "willingness_to_call" in data.columns

    descriptions = {
        "Cultural & Linguistic": (
            "Survey language is an administrative field; it doesn't measure "
            "family attitudes or the cultural fit of the training."
        ),
        "Socioeconomic & Practical": (
            "Practical access barriers such as phone/internet, cost, "
            "time, or a private space were not directly asked about."
        ),
        "Communication": (
            "The original survey asks about calling, not preferred texting "
            "or chat contact methods or communication accessibility."
        ),
        "Institutional Trust": (
            "Counselor trust, confidentiality, and emergency involvement "
            "were not directly assessed."
        ),
        "Psychological": (
            "Emotional comfort and the feeling that one's situation "
            "merits support were not directly assessed."
        ),
    }
    rows = []
    for dimension, question_ids in _DIMENSION_QUESTIONS.items():
        directly_asked = [
            qid for qid in question_ids if mapped["by_id"].get(qid)
        ]
        headers = sorted({
            header for qid in directly_asked for header in mapped["by_id"][qid]
        })
        if directly_asked:
            status = "Directly measured"
            summary = (
                f"{len(headers)} added question(s) directly address this dimension. "
                "That doesn't establish that every aspect of the dimension is covered."
            )
        elif (dimension == "Cultural & Linguistic" and has_language) or (
            dimension == "Communication" and has_call_intent
        ):
            status = "Partially measured"
            summary = descriptions[dimension]
        else:
            status = "Not directly measured"
            summary = descriptions[dimension]
        rows.append({
            "dimension": dimension,
            "coverage": status,
            "explanation": summary,
            "question_count": len(headers),
            "matched_question_ids": directly_asked,
            "matched_question_headers": headers,
            "unmeasured_question_ids": [
                qid for qid in question_ids if qid not in directly_asked
            ],
        })
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
    """Use Person 4's original detection/recommendation rules on the new file.

    Coverage is re-audited from questionnaire columns every time. Existing
    core survey measures must remain available; supplemental question columns
    may be added freely. Person 2 and 3 findings can be passed in via the
    original external_findings contract.
    """
    data = standardize_survey(df)
    coverage = coverage_audit(data)
    recognized = identify_direct_questions(data)

    automatic_findings, summary = detect_findings(data)

    # The original detector assumes the base survey asks only about calls.
    # Do not repeat that claim once a new text/chat preference item exists.
    if recognized["by_id"]["COM01"]:
        automatic_findings = [
            finding for finding in automatic_findings
            if finding["type"] != "call_only_measure"
        ]

    # Missing questionnaire topics are real design gaps, not participant
    # outcomes. They are low-priority fallbacks behind observed signals.
    for _, dimension in coverage.iterrows():
        for question_id in dimension["unmeasured_question_ids"]:
            if question_id == "COM01" and recognized["by_id"]["COM01"]:
                continue
            automatic_findings.append(make_finding(
                finding_type=f"questionnaire_missing_{question_id.lower()}",
                title=f"Current survey does not directly ask {question_id}",
                description=(
                    f"Question {question_id} could help measure "
                    f"{dimension['dimension']}. This is a questionnaire "
                    "coverage gap, not a demonstrated respondent barrier."
                ),
                source="questionnaire_coverage",
                limitations=[
                    "No participant-level barrier can be inferred from a missing question.",
                    "The questionnaire matching rules require staff review.",
                ],
                evidence={
                    "dimension": dimension["dimension"],
                    "question_id": question_id,
                    "status": dimension["coverage"],
                },
            ))

    findings_by_type = {
        finding["type"]: finding for finding in automatic_findings
    }
    team_findings = prepare_external_findings(external_findings)
    for finding in team_findings:
        findings_by_type[finding["type"]] = finding
    combined_findings = list(findings_by_type.values())

    # Preserve the original rule mapping; layer on a transparent priority and
    # remove suggestions that the revised questionnaire already includes.
    recommendations = recommend_questions(combined_findings)
    already_asked = {
        qid for qid, headers in recognized["by_id"].items() if headers
    }
    if not recommendations.empty:
        recommendations = recommendations[
            ~recommendations["question_id"].isin(already_asked)
        ].copy()

        source_weight = {
            "person2_gap_detector": 100,
            "person3_feedback_themes": 90,
            "keyword_screening": 60,
            "accessibility_audit": 45,
            "questionnaire_coverage": 15,
        }
        recommendations["priority"] = recommendations["evidence_sources"].map(
            lambda sources: (
                max((source_weight.get(name, 10) for name in sources), default=0)
                + 2 * max(0, len(sources) - 1)
            )
        )
        recommendations = recommendations.sort_values(
            ["priority", "question_id"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)

    return {
        "summary": summary,
        "coverage": coverage,
        "findings": combined_findings,
        "recommendations": recommendations,
        "question_bank": pd.DataFrame(question_bank),
        "recognized_question_ids": sorted(already_asked),
        "supplemental_question_columns": recognized["supplemental_columns"],
        "unclassified_question_columns": [
            header for header in recognized["supplemental_columns"]
            if header not in recognized["recognized_columns"]
        ],
        "team_findings_count": len(team_findings),
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
    Friendly front-end for the same question-bank and recommendation functions.

    All original evidence, audit tables, question previews and CSV export are
    still available. Only their visual order and defaults have changed.
    """
    import streamlit as st
    from ui_styles import intro, stat_cards, focus_card

    intro(
        "HELP EVERYMIND LEARN WHAT THE SURVEY MISSES",
        "Ask better questions next time",
        "See what's measurable now, explore suggested follow-up questions, "
        "and build a more inclusive future survey.",
    )

    summary = report["summary"]
    recommendations = report["recommendations"]
    findings = report["findings"]
    coverage = report["coverage"]

    stat_cards([
        {
            "icon": "💜", "tone": "lilac",
            "label": "Survey responses",
            "value": f"{summary['total_responses']:,}",
            "detail": "Current data selection",
        },
        {
            "icon": "🔎", "tone": "peach",
            "label": "Call-intent answers missing",
            "value": f"{summary['missing_call_percent']:.1f}%",
            "detail": "Does not mean unwillingness",
        },
        {
            "icon": "📝", "tone": "mint",
            "label": "Draft question bank",
            "value": str(len(question_bank)),
            "detail": "Optional questions for EveryMind review",
        },
    ])

    st.write("")
    focus_card(
        "THE OPPORTUNITY",
        "Awareness isn't the same as accessibility",
        "The existing survey asks about calling 988, but not preferred contact "
        "methods, trust, practical access, or emotional comfort. "
        "A short follow-up can help EveryMind learn rather than assume.",
    )

    st.subheader("What isn't being measured yet?")
    st.caption(
        "These are survey-design gaps, not evidence that specific participant groups face them."
    )

    for _, row in coverage.iterrows():
        with st.expander(f"{row['dimension']} · {row['coverage']}"):
            st.write(row["explanation"])

    with st.expander("View the complete coverage table"):
        st.dataframe(coverage, hide_index=True, width="stretch")

    st.write("")
    st.subheader("Recommended follow-up questions")
    st.caption(
        "Suggestions change with the data and are linked to observations. "
        "A keyword mention alone does not establish a barrier."
    )

    if recommendations.empty:
        st.info(
            "No detection rule recommended a specific question for this selection. "
            "You can still choose from the complete question bank below."
        )
    else:
        for _, item in recommendations.iterrows():
            with st.expander(
                f"{item['question_id']} · {item['question']}"
            ):
                st.caption(item["dimension"])
                st.markdown("**Why consider this question?**")
                for reason in item["why_recommended"]:
                    st.write("- " + reason)
                st.markdown("**Response options**")
                for option in item["options"]:
                    st.write("- " + option)
                st.write("**What we'd learn:** " + item["purpose"])
                st.caption(
                    "Signals: " + ", ".join(item["evidence_sources"])
                )

    with st.expander("Show the detected findings and their limitations"):
        if not findings:
            st.info("No findings were produced for this selection.")
        for finding in findings:
            st.markdown("**" + finding["title"] + "**")
            st.write(finding["description"])
            if finding.get("count") is not None:
                st.caption(
                    f"Matched: {finding['count']} of "
                    f"{finding.get('denominator', 'unknown denominator')}"
                )
            st.caption("Source: " + finding["source"])
            for limitation in finding.get("limitations", []):
                st.caption("• " + limitation)
            st.divider()

    st.write("")
    st.subheader("Build your next survey")
    st.caption(
        "Choose the questions you'd like to propose. Nothing is sent to participants; "
        "you'll download a draft for EveryMind's review."
    )

    question_lookup = {
        q["id"]: q for q in question_bank
    }
    recommended_ids = recommendations["question_id"].tolist()

    selected_ids = st.multiselect(
        "Select draft questions",
        options=list(question_lookup),
        default=recommended_ids,
        format_func=lambda qid: (
            f"{qid} — {question_lookup[qid]['question']}"
        ),
    )

    with st.expander("Preview your selected questions"):
        if not selected_ids:
            st.caption("Select questions above to preview them here.")
        for qid in selected_ids:
            q = question_lookup[qid]
            st.markdown(f"**{qid}: {q['question']}**")
            st.caption(q["dimension"])
            for option in q["options"]:
                st.write("- " + option)
            st.caption("Purpose: " + q["purpose"])
            st.divider()

    st.download_button(
        "Download draft questions (CSV)",
        data=export_selected_questions(selected_ids),
        file_name="everymind_followup_questions.csv",
        mime="text/csv",
        disabled=not selected_ids,
        key="survey_designer_csv_download",
    )

    with st.expander("Browse all 10 draft questions"):
        st.dataframe(report["question_bank"], hide_index=True, width="stretch")

    st.caption(
        "Draft questions are not validated survey instruments. EveryMind should "
        "review wording, accessibility, consent, and participant safety before use."
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