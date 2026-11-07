"""
sample_findings.py  (Person 5)
==============================
FAKE (synthetic) findings and metrics used to build and demo the Action Lab
before the real analysis from the other teammates is ready.

IMPORTANT:
  * Everything in this file is FICTIONAL. None of it is an EveryMind result.
  * Every finding has status = "synthetic" so the app and the PDF can
    show the "SYNTHETIC DEMONSTRATION" warning automatically.
  * When real results are ready, build findings with the SAME fields
    (see FINDING_FIELDS below) and pass them to the same functions.
    Missing values should be None (NOT zero).

This file does NOT import streamlit, so any module can import it.
"""

# The standard fields every finding should have (the "shared interface").
FINDING_FIELDS = [
    "id",           # unique text id, e.g. "gap_001"
    "source",       # which module made it: "gap_detector", "feedback_analyzer", "accessibility_audit"
    "type",         # finding type (decides which interventions we suggest)
    "title",        # short title
    "description",  # one or two sentences
    "count",        # numerator (None if unknown)
    "denominator",  # denominator (None if unknown)
    "percentage",   # percent 0-100 (None if unknown)
    "limitations",  # list of short caveat strings
    "evidence",     # dict with any extra details
    "status",       # "synthetic", "validated", "unvalidated", ...
]


def _pct(count, denominator):
    """Return count/denominator as a percent rounded to 1 decimal (None if impossible)."""
    if count is None or not denominator:
        return None
    return round(100.0 * count / denominator, 1)


def _make(id_, source, type_, title, description, count, denominator, limitations):
    """Small helper that builds one synthetic finding with all standard fields."""
    return {
        "id": id_,
        "source": source,
        "type": type_,
        "title": "[SYNTHETIC] " + title,
        "description": "SYNTHETIC DEMO - not a real finding. " + description,
        "count": count,
        "denominator": denominator,
        "percentage": _pct(count, denominator),
        "limitations": ["Synthetic data - fictional numbers"] + limitations,
        "evidence": {},
        "status": "synthetic",
    }


# ---------------------------------------------------------------------------
# 10 synthetic findings. They cover each trigger type in the matching rules,
# plus one finding with an UNKNOWN type and MISSING numbers (to test "Needs review").
# ---------------------------------------------------------------------------
SYNTHETIC_FINDINGS = [
    _make("synthetic_001", "gap_detector", "knowledge_action_gap",
          "Illustrative knowledge/action pattern",
          "Some participants rated their knowledge high but call intent low.",
          25, 140, ["Incomplete call-intent coverage", "Self-reported ratings"]),

    _make("synthetic_002", "gap_detector", "low_when_knowledge",
          "Illustrative low 'knowing when to use 988' pattern",
          "Fewer participants agreed with 'I know when to use 988' than with the other two knowledge items.",
          48, 150, ["Recalled-before ratings may be biased", "No causal claim"]),

    _make("synthetic_003", "accessibility_audit", "communication_measurement_gap",
          "Illustrative contact-method gap",
          "The survey asks about calling only, not about text or chat preferences.",
          None, None, ["This is a measurement gap, not a participant result"]),

    _make("synthetic_004", "accessibility_audit", "privacy_measurement_gap",
          "Illustrative privacy/trust not measured",
          "The survey has no question about privacy or trust.",
          None, None, ["Trust is not measured; do not claim a trust problem"]),

    _make("synthetic_005", "feedback_analyzer", "privacy_feedback_concern",
          "Illustrative privacy comments",
          "A few open-ended comments mention privacy concerns.",
          6, 90, ["Small number of comments", "Comment themes need manual validation"]),

    _make("synthetic_006", "feedback_analyzer", "requests_more_examples",
          "Illustrative requests for more examples",
          "Several comments ask for more real-life examples.",
          14, 90, ["Comment themes need manual validation"]),

    _make("synthetic_007", "gap_detector", "low_presenter_engagement",
          "Illustrative lower presenter-engagement ratings",
          "Presenter-engagement ratings were lower for one group of sessions.",
          22, 120, ["Different session sizes", "Ratings are self-reported"]),

    _make("synthetic_008", "gap_detector", "small_group_sample",
          "Illustrative small-sample group difference",
          "One county or role group looks different but has very few responses.",
          7, 9, ["Very small sample - do not over-interpret"]),

    _make("synthetic_009", "gap_detector", "low_call_intent_response_rate",
          "Illustrative low response rate on call-intent question",
          "Many participants left the 'likely to call 988' question blank.",
          95, 140, ["Blank answers may not be random", "Reason for blanks is unknown"]),

    # A finding with an unknown type and missing numbers -> should show "Needs review".
    {
        "id": "synthetic_010",
        "source": "unknown_module",
        "type": "unrecognized_type_example",
        "title": "[SYNTHETIC] Finding with unknown type and missing numbers",
        "description": "SYNTHETIC DEMO - not a real finding. Used to test the 'Needs review' state.",
        "count": None,
        "denominator": None,
        "percentage": None,
        "limitations": ["Synthetic data - fictional numbers", "Type not recognized by the planner"],
        "evidence": {},
        "status": "synthetic",
    },
]


# ---------------------------------------------------------------------------
# Synthetic report metrics (used by report_generator.generate_report).
# Every key is OPTIONAL in the real report. Missing = shown as "Not available".
# ---------------------------------------------------------------------------
SYNTHETIC_METRICS = {
    "status": "synthetic",                 # "synthetic" turns on the demo warning
    "dataset_period": "FICTIONAL: Jan 2000 - Feb 2000",
    "n_responses": 150,
    "responses_verified": False,           # only True when the real count was checked

    # Three knowledge measures (recalled-before vs current). Means are on the dataset's rating scale.
    "scale_note": "Synthetic ratings on a 1-5 scale (illustrative only).",
    "scale_max": 5,
    "knowledge": [
        {"measure": "Identify mental health challenges and crises",
         "before_mean": 3.1, "current_mean": 4.2, "n_paired": 138},
        {"measure": "Describe 988 and how it works",
         "before_mean": 2.6, "current_mean": 4.3, "n_paired": 140},
        {"measure": "Know when to use 988",
         "before_mean": 2.9, "current_mean": 4.0, "n_paired": 135},
    ],

    # Call-intent coverage (how many answered the 'likely to call 988' question).
    "call_intent": {"n_answered": 45, "n_total": 140},
    "knowledge_call_relationship": {
        "summary": "SYNTHETIC: participants with higher knowledge ratings tended to report higher call intent "
                   "(illustrative only; relationship, not cause).",
        "n": 45,
    },

    # Comment themes. Only validated themes are reported in the PDF.
    "themes": [
        {"theme": "Requests for more examples", "count": 14, "denominator": 90, "validated": True},
        {"theme": "Privacy concerns", "count": 6, "denominator": 90, "validated": True},
        {"theme": "Wants shorter session", "count": 9, "denominator": 90, "validated": False},
    ],
    "approved_excerpts": [],               # leave empty unless excerpts are approved and de-identified

    # How well each accessibility dimension is covered by the survey.
    # Allowed words: "Measured", "Indirectly mentioned", "Unmeasured"
    "dimension_status": {
        "Cultural and social norms": "Unmeasured",
        "Practical / socioeconomic": "Unmeasured",
        "Communication access": "Indirectly mentioned",
        "Institutional trust": "Unmeasured",
        "Psychological comfort": "Unmeasured",
    },
}


def get_synthetic_findings():
    """Return a fresh COPY of the synthetic findings (so edits do not change the originals)."""
    return [dict(f, limitations=list(f["limitations"]), evidence=dict(f["evidence"]))
            for f in SYNTHETIC_FINDINGS]


def get_synthetic_metrics():
    """Return a fresh COPY of the synthetic metrics."""
    import copy
    return copy.deepcopy(SYNTHETIC_METRICS)