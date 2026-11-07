import pandas as pd

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
    "low_call_intent_response_rate": ["COM01", "PSY02"],
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
