"""
intervention_planner.py  (Person 5)
===================================
Turns FINDINGS (from the gap detector, feedback analyzer, accessibility audit)
into candidate training IMPROVEMENTS ("interventions").

Three functions other modules can call (NO streamlit needed):
    recommend_interventions(findings)           -> dict of recommendations
    build_action_plan(findings, selected_ids)   -> list of plan rows (one per chosen action)
    (generate_report lives in report_generator.py)

Rules we follow (so we never overclaim):
  * Missing values stay missing (None). We never turn them into zero.
  * We never invent numbers, subgroups, "impact scores" or claims about 988 confidentiality.
  * "Effort" is a planning ESTIMATE only, never a proven impact.
  * Unknown finding types -> a safe "Needs review" state (no invented advice).
"""

import copy
import math

# ---------------------------------------------------------------------------
# 1. THE INTERVENTION CATALOG
#    12 catalog options from the brief + 2 "process" actions
#    ("collect more evidence first" and "fix the survey question").
#    To EDIT an option, just change the text below.
# ---------------------------------------------------------------------------
INTERVENTIONS = {

    "myth_vs_reality": {
        "title": "988 Myth vs. Reality",
        "kind": "catalog",
        "summary": "Add a short fact-check segment that addresses common misconceptions, "
                   "using only wording verified with official 988 / EveryMind sources.",
        "outcome": "Participants can tell misconceptions from verified facts and feel more confident about seeking help.",
        "trigger_text": "Knowledge/action disconnect, or explicit misconception comments.",
        "why": "Some participants may know about 988 yet still hesitate. Misconceptions are one possible "
               "reason, but the survey can only hint at this through comments.",
        "steps": [
            "List misconceptions using ONLY validated comments or presenter experience.",
            "Ask EveryMind staff to verify the correct facts against official 988 sources.",
            "Add a short 'Myth vs. Reality' segment to the slides.",
            "Add 2-3 optional quiz items on misconception accuracy plus one help-seeking confidence item.",
        ],
        "owner": "Training content lead with an EveryMind reviewer",
        "effort": "Medium",
        "metric": "Share answering the misconception items correctly; self-rated confidence about seeking help.",
        "checkin": "After the first 2-3 sessions that use the segment",
        "unanswered": [
            "Which misconceptions are actually common among participants?",
            "Is misunderstanding the reason for low call intent?",
        ],
        "change_mind": "If most participants already answer misconception items correctly, or comments rarely "
                       "mention misconceptions, drop this and investigate comfort or measurement limits instead.",
        "caveats": ["The survey does not measure misconceptions directly.",
                    "Fact wording must be verified by EveryMind before use."],
    },

    "contact_method": {
        "title": "Choose Your Contact Method",
        "kind": "catalog",
        "summary": "Teach the verified call, text, and chat routes and ask an optional contact-method preference question.",
        "outcome": "Participants know which contact routes exist and which feels most comfortable to them.",
        "trigger_text": "Call/text/chat preferences are not measured.",
        "why": "The survey asks about willingness to CALL. Willingness to call is not willingness to text or chat, "
               "so some people's preferences are invisible in the data.",
        "steps": [
            "Confirm the current call, text, and chat options with EveryMind (verified wording only).",
            "Add a short slide that explains each route in plain language.",
            "Add one optional survey question about preferred contact method.",
            "Review results by route to see which options participants say they would use.",
        ],
        "owner": "EveryMind program staff + survey owner",
        "effort": "Low",
        "metric": "Response rate and distribution on the optional contact-method question; knowledge of available routes.",
        "checkin": "After the next training cycle",
        "unanswered": [
            "Which contact method do participants prefer?",
            "Do preferences differ by language or role? (Check sample sizes first.)",
        ],
        "change_mind": "If nearly everyone already prefers calling and knows the other routes, "
                       "this is low priority; focus on other barriers.",
        "caveats": ["Contact-method preference is not measured in the current survey."],
    },

    "crisis_scenarios": {
        "title": "Real-World Crisis Scenarios",
        "kind": "catalog",
        "summary": "Use realistic, non-graphic scenarios that practice deciding when 988 is appropriate.",
        "outcome": "Participants get better at recognizing when to use 988.",
        "trigger_text": "Low knowledge of when to use 988, or requests for examples.",
        "why": "Participants who are unsure WHEN to use 988 may benefit from practicing with examples.",
        "steps": [
            "Write 3-4 short, non-graphic scenarios (including 'not sure if it's a crisis' situations).",
            "Have an EveryMind reviewer check them for safety and accuracy.",
            "Run them as a short group discussion or poll.",
            "Add a scenario-based question (which action fits?) before and after.",
        ],
        "owner": "Training content lead + EveryMind reviewer",
        "effort": "Medium",
        "metric": "Scenario-based decision accuracy; the 'I know when to use 988' rating.",
        "checkin": "After 2-3 sessions",
        "unanswered": [
            "Is low 'when to use' knowledge caused by lack of examples or by something else?",
        ],
        "change_mind": "If scenario-question performance is already strong, adding more scenarios may not "
                       "help; investigate comfort or measurement limits instead.",
        "caveats": ["Recalled-before ratings are self-reported and may be biased."],
    },

    "confidentiality_explained": {
        "title": "Confidentiality Explained",
        "kind": "catalog",
        "summary": "Explain verified privacy practices and their limits, and ask an optional clarity/confidence question.",
        "outcome": "Participants understand what is and is not private, so privacy fears are less of a barrier.",
        "trigger_text": "Explicit privacy concern in comments, or unmeasured trust (research first).",
        "why": "Privacy may matter to participants. If it is only unmeasured (not mentioned), treat this as "
               "a topic to investigate, not as a confirmed problem.",
        "steps": [
            "Ask EveryMind for approved wording about privacy practices AND their limits.",
            "Add a short, plain-language segment or FAQ slide using only that wording.",
            "Add an optional question about how clear the privacy explanation was.",
            "Review privacy-related comments for new questions to answer.",
        ],
        "owner": "EveryMind program staff (approves wording) + training content lead",
        "effort": "Low",
        "metric": "Self-rated clarity/confidence about privacy; number of privacy-related comments.",
        "checkin": "After the next training cycle",
        "unanswered": [
            "Do participants actually worry about privacy, or is this just not measured?",
        ],
        "change_mind": "If participants already rate privacy clarity high, or privacy is never mentioned, "
                       "do not add more privacy content.",
        "caveats": ["No claims about 988 confidentiality should be made without EveryMind verification.",
                    "Trust is not directly measured."],
    },

    "culturally_responsive_scenarios": {
        "title": "Culturally Responsive Scenarios",
        "kind": "catalog",
        "summary": "Co-design scenarios set in varied family and community contexts with community partners.",
        "outcome": "Participants find the examples relevant and understandable.",
        "trigger_text": "Comments request more relatable examples.",
        "why": "People may relate to examples differently. We should not assume group-level beliefs; "
               "partners can help us build varied, respectful examples.",
        "steps": [
            "Invite community partners to review and suggest example contexts.",
            "Write several varied scenarios (different family, school, work and community settings).",
            "Pilot them and ask an optional 'Did the examples feel relevant to you?' question.",
            "Revise based on feedback.",
        ],
        "owner": "Training content lead + community partners",
        "effort": "High",
        "metric": "Relevance rating of examples; comprehension of scenario questions.",
        "checkin": "After a pilot with 2-3 sessions",
        "unanswered": [
            "Which contexts feel relevant to which participants? (Not measured today.)",
        ],
        "change_mind": "If relevance ratings are already high across groups, keep current examples and "
                       "look at other barriers.",
        "caveats": ["Do not stereotype communities or infer group beliefs from county labels."],
    },

    "low_pressure_participation": {
        "title": "Low-Pressure Participation",
        "kind": "catalog",
        "summary": "Offer anonymous Q&A and opt-in written exercises so nobody has to speak up or share personal details.",
        "outcome": "More participants feel comfortable taking part.",
        "trigger_text": "Comments indicate discomfort speaking publicly.",
        "why": "Some people may avoid speaking in groups. Anonymous options let them take part without disclosure.",
        "steps": [
            "Add an anonymous question box (paper or digital).",
            "Offer opt-in written exercises instead of speaking out loud.",
            "State clearly that no personal disclosure is required.",
            "Ask an optional question about participation comfort.",
        ],
        "owner": "Presenters / facilitators",
        "effort": "Low",
        "metric": "Self-rated participation comfort; number of anonymous questions received.",
        "checkin": "After 2-3 sessions",
        "unanswered": [
            "How many participants feel uncomfortable participating? (Not measured today.)",
        ],
        "change_mind": "If participation comfort is already high, do not add more format changes for this reason.",
        "caveats": ["Do not infer trauma or mental-health history from participation comfort."],
    },

    "presenter_improvement_loop": {
        "title": "Presenter Improvement Loop",
        "kind": "catalog",
        "summary": "Review facilitation and pacing with presenters using ratings and suggestions.",
        "outcome": "Higher and more consistent presenter-engagement ratings.",
        "trigger_text": "Low engagement ratings or recurring presentation comments.",
        "why": "Engagement ratings and comments may point to delivery details that can be improved.",
        "steps": [
            "Share session-level engagement ratings and validated suggestions with presenters.",
            "Agree on 1-2 changes (e.g., pacing, interaction) to try.",
            "Run the next sessions with those changes.",
            "Compare ratings and suggestions before vs. after.",
        ],
        "owner": "Training lead + presenters",
        "effort": "Low",
        "metric": "Presenter-engagement rating by session; recurring suggestion themes.",
        "checkin": "After the next 3 sessions",
        "unanswered": [
            "Are differences due to presenter, audience, room, or session size?",
        ],
        "change_mind": "If differences vanish after accounting for session size or audience type, "
                       "do not blame delivery.",
        "caveats": ["Observational ratings; session differences are not proof of cause."],
    },

    "format_experiment": {
        "title": "Format Experiment",
        "kind": "catalog",
        "summary": "Pilot two formats (e.g., shorter vs. more interactive) and compare comparable outcomes and satisfaction.",
        "outcome": "Learn which format works better for which setting.",
        "trigger_text": "Requests for shorter or more interactive sessions.",
        "why": "If comments request a different format, a small test is better than guessing.",
        "steps": [
            "Pick two formats to compare.",
            "Run each with similar audiences where possible.",
            "Use the same survey questions for both.",
            "Compare knowledge ratings and satisfaction, noting sample sizes.",
        ],
        "owner": "Training lead + survey owner",
        "effort": "Medium",
        "metric": "Knowledge ratings and satisfaction by format.",
        "checkin": "After both formats have been run at least a few times",
        "unanswered": ["Do audiences differ between formats?"],
        "change_mind": "If audiences are too different to compare fairly, treat results as exploratory only.",
        "caveats": ["Not a randomized experiment unless designed as one."],
    },

    "community_partner_review": {
        "title": "Community Partner Review",
        "kind": "catalog",
        "summary": "Ask local partners to interpret a subgroup difference and co-design any response before targeting any group.",
        "outcome": "Interpretations come from people who know the local context, not from assumptions.",
        "trigger_text": "A supported subgroup difference with an adequate sample.",
        "why": "A difference between groups does not explain itself. Partners can add context and "
               "help avoid unfair conclusions.",
        "steps": [
            "Share the finding (aggregate only) with partners, including its limits.",
            "Ask what might explain it and what would help.",
            "Co-design any change with them.",
            "Agree on how to measure whether it helped.",
        ],
        "owner": "EveryMind community outreach lead",
        "effort": "Medium",
        "metric": "Partner feedback; follow-up difference between groups (with sample sizes).",
        "checkin": "Within the next training cycle",
        "unanswered": ["Why does the difference exist?"],
        "change_mind": "If the difference disappears with more data or is due to sample size, do not act on it.",
        "caveats": ["Only use when the sample is adequate.", "Do not infer group identity from county labels."],
    },

    "accessibility_question_pack": {
        "title": "Accessibility Question Pack",
        "kind": "catalog",
        "summary": "Add optional questions about practical, cultural, trust, and communication barriers.",
        "outcome": "Future surveys can show which barriers exist, instead of guessing.",
        "trigger_text": "Unmeasured practical, cultural, trust, or communication barriers.",
        "why": "The current survey does not measure these barriers, so we cannot say whether they matter. "
               "Optional questions close that gap.",
        "steps": [
            "Pick a short set of optional questions (see the Inclusive Action Lens tab).",
            "Make every question optional, with a 'prefer not to say' choice.",
            "Add them to the next survey version.",
            "Track how many people answer and how comfortable they feel.",
        ],
        "owner": "Survey owner + EveryMind program staff",
        "effort": "Low",
        "metric": "Response coverage for each new question; participant comfort with the questions.",
        "checkin": "After the next survey version is used",
        "unanswered": ["Which barriers matter most? (This is what the pack is for.)"],
        "change_mind": "If very few people answer or many skip, rewrite or move the questions before drawing conclusions.",
        "caveats": ["New questions do not by themselves improve training; they improve what we can learn."],
    },

    "retention_followup": {
        "title": "Retention Follow-up",
        "kind": "catalog",
        "summary": "Offer an optional later follow-up to see what participants still remember.",
        "outcome": "Learn whether knowledge lasts after the training.",
        "trigger_text": "Only immediate post-training measurement is available.",
        "why": "The survey is taken right after training, so we cannot tell what is remembered later.",
        "steps": [
            "Decide on a follow-up time (a planning choice for EveryMind).",
            "Collect optional contact information with consent.",
            "Send a short follow-up with the same knowledge items.",
            "Compare responders with non-responders to check for response bias.",
        ],
        "owner": "Survey owner + EveryMind program staff",
        "effort": "Medium",
        "metric": "Retention of knowledge ratings at follow-up; follow-up response rate.",
        "checkin": "At the chosen follow-up time",
        "unanswered": ["Do people who respond differ from people who do not?"],
        "change_mind": "If follow-up response is very low, results may not represent participants; try a shorter follow-up.",
        "caveats": ["Follow-up responders may differ from non-responders."],
    },

    "help_seeking_confidence": {
        "title": "Help-Seeking Confidence Exercise",
        "kind": "catalog",
        "summary": "Explain what contacting 988 can involve and practice getting ready to reach out, without forcing anyone to disclose anything.",
        "outcome": "Participants feel more confident about what reaching out involves.",
        "trigger_text": "High knowledge but low call intent.",
        "why": "Knowing about 988 is not the same as feeling ready to use it. A walk-through may lower uncertainty.",
        "steps": [
            "Ask EveryMind for a verified plain-language description of what contacting 988 can involve.",
            "Add a short, no-disclosure walk-through to the training.",
            "Include the message that you do not have to be sure it is a crisis to reach out (verified wording only).",
            "Add an optional 'How confident would you feel contacting 988?' question.",
        ],
        "owner": "Training content lead + EveryMind reviewer",
        "effort": "Medium",
        "metric": "Self-rated confidence about contacting 988; call-intent rating (with response coverage).",
        "checkin": "After 2-3 sessions",
        "unanswered": [
            "Is low call intent caused by confidence, trust, stigma, or something else? (Not measured.)",
        ],
        "change_mind": "If confidence is already high but call intent is still low, look at trust, "
                       "contact-method, or measurement issues instead.",
        "caveats": ["Call intent has incomplete coverage.", "Do not claim that this will raise call intent."],
    },

    # ---- Process actions (not in the 12 catalog items; used by the matching rules) ----
    "collect_more_evidence": {
        "title": "Collect more evidence first",
        "kind": "process",
        "summary": "Do not act yet. Gather more responses before changing the training.",
        "outcome": "A sample large enough to interpret safely.",
        "trigger_text": "A small group sample.",
        "why": "Very small groups give unstable results, so acting now could be misleading.",
        "steps": [
            "Set a minimum number of responses before reporting this group (agree with the team).",
            "Keep collecting responses in future sessions.",
            "Re-run the analysis once the minimum is reached.",
            "Decide on action only after that.",
        ],
        "owner": "Survey owner / data analyst",
        "effort": "Low",
        "metric": "Number of responses in the group versus the agreed minimum.",
        "checkin": "After each new data upload",
        "unanswered": ["Does the pattern hold with more data?"],
        "change_mind": "If the pattern disappears with more data, drop it. If it holds, consider Community Partner Review.",
        "caveats": ["The minimum sample size is a team decision, not a fixed rule."],
    },

    "survey_design_fix": {
        "title": "Improve survey question design/placement",
        "kind": "process",
        "summary": "Check why many people skipped the call-intent question and fix its wording, placement, or format.",
        "outcome": "More complete answers to the call-intent question.",
        "trigger_text": "Low response rate on the call-intent question.",
        "why": "If many people skip it, we cannot trust conclusions about willingness to call.",
        "steps": [
            "Check where the question appears in the survey and how it is worded.",
            "Test a clearer wording or a different position.",
            "Make sure it is not hidden or skipped by survey logic.",
            "Compare response rates before vs. after.",
        ],
        "owner": "Survey owner",
        "effort": "Low",
        "metric": "Response rate on the call-intent question.",
        "checkin": "After the next survey version",
        "unanswered": ["Why are people skipping it? (Reason is unknown.)"],
        "change_mind": "If response rate is already high after checking, look at who is skipping before changing the question.",
        "caveats": ["Blank answers may not be random."],
    },
}

# Order used when we show the full catalog ("Explore more").
CATALOG_ORDER = [
    "myth_vs_reality", "contact_method", "crisis_scenarios", "confidentiality_explained",
    "culturally_responsive_scenarios", "low_pressure_participation", "presenter_improvement_loop",
    "format_experiment", "community_partner_review", "accessibility_question_pack",
    "retention_followup", "help_seeking_confidence", "collect_more_evidence", "survey_design_fix",
]

# ---------------------------------------------------------------------------
# 2. MATCHING RULES: finding type -> 1 to 3 intervention ids (first = first recommendation)
#    The first 9 rows come straight from the brief. The last 4 are extra types so
#    that every catalog option can be reached.
# ---------------------------------------------------------------------------
FINDING_TYPE_MAP = {
    "knowledge_action_gap": ["help_seeking_confidence", "myth_vs_reality"],
    "low_when_knowledge": ["crisis_scenarios", "retention_followup"],
    "communication_measurement_gap": ["contact_method", "accessibility_question_pack"],
    "privacy_measurement_gap": ["accessibility_question_pack", "confidentiality_explained"],
    "privacy_feedback_concern": ["confidentiality_explained", "low_pressure_participation"],
    "requests_more_examples": ["crisis_scenarios", "culturally_responsive_scenarios"],
    "low_presenter_engagement": ["presenter_improvement_loop", "format_experiment"],
    "small_group_sample": ["collect_more_evidence", "community_partner_review"],
    "low_call_intent_response_rate": ["survey_design_fix", "accessibility_question_pack"],
    # Extra types (not in the brief's table):
    "requests_format_change": ["format_experiment", "low_pressure_participation"],
    "participation_discomfort": ["low_pressure_participation", "presenter_improvement_loop"],
    "supported_subgroup_difference": ["community_partner_review", "culturally_responsive_scenarios"],
    "immediate_only_measurement": ["retention_followup", "accessibility_question_pack"],
}

# Special notes for specific (finding type, intervention) pairs.
PAIR_NOTES = {
    ("privacy_measurement_gap", "confidentiality_explained"):
        "Suggested ONLY as a topic to investigate. Trust/privacy is not measured, so do not claim a problem exists.",
    ("small_group_sample", "community_partner_review"):
        "Only after enough responses are collected. Do not target any group on a tiny sample.",
}

# ---------------------------------------------------------------------------
# 3. INCLUSIVE ACTION LENS: the five accessibility dimensions
# ---------------------------------------------------------------------------
DIMENSIONS = {
    "Cultural and social norms": {
        "established": "The survey records county, role and language only. It has no direct measure of family, "
                       "community or cultural views about mental health.",
        "unknown": "Whether cultural norms, stigma, or gender expectations affect willingness to seek support.",
        "design_choices": [
            "Use scenarios set in several family and community contexts.",
            "Co-design scenarios with community partners.",
            "Add optional stigma questions.",
        ],
        "future_questions": [
            "Optional: 'Did the examples in the training feel relevant to your community? (Yes / Somewhat / No / Prefer not to say)'",
            "Optional: 'How comfortable would you feel talking about mental health with people around you?'",
        ],
        "interpretation": "Do not stereotype communities or claim group stigma from county labels.",
        "intervention_ids": ["culturally_responsive_scenarios", "community_partner_review",
                             "low_pressure_participation", "accessibility_question_pack"],
    },
    "Practical / socioeconomic": {
        "established": "The survey has no data on income, transportation, insurance, time, or privacy at home.",
        "unknown": "Whether cost, time, privacy, or access get in the way of seeking support.",
        "design_choices": [
            "Offer short modules and flexible delivery.",
            "Use privacy-aware exercises.",
            "Add optional practical-barrier questions.",
        ],
        "future_questions": [
            "Optional: 'Which of these would make it easier to reach out for support? (Time, privacy, cost, transportation, other)'",
        ],
        "interpretation": "No direct income or resource-access inference can be made from this dataset.",
        "intervention_ids": ["format_experiment", "accessibility_question_pack", "retention_followup"],
    },
    "Communication access": {
        "established": "The survey asks about willingness to CALL 988 only.",
        "unknown": "Preferences for text or chat, language needs, and accessible formats.",
        "design_choices": [
            "Teach call, text and chat routes (verified).",
            "Use plain-language materials.",
            "Run a language-access review of the training.",
        ],
        "future_questions": [
            "Optional: 'Which of the following would make you more comfortable reaching out for mental health support?' "
            "(Ability to text instead of call / Clear explanation of confidentiality / Support in a preferred language / "
            "Reassurance that you don't need to be suicidal / Information about when emergency services may be contacted / Something else)",
        ],
        "interpretation": "Willingness to call is not willingness to text or chat.",
        "intervention_ids": ["contact_method", "accessibility_question_pack", "presenter_improvement_loop"],
    },
    "Institutional trust": {
        "established": "Trust is not directly measured. Only explicit, validated comments could support a narrow claim.",
        "unknown": "Whether concerns about privacy, police, hospitalization or surveillance affect willingness to call.",
        "design_choices": [
            "Create a verified confidentiality FAQ.",
            "Be transparent about limits.",
            "Add optional trust questions.",
        ],
        "future_questions": [
            "Optional: 'How clear was the explanation of what happens when someone contacts 988?'",
            "Optional: 'Is there something about contacting 988 that worries you? (Optional)'",
        ],
        "interpretation": "Do not state or imply facts about 988 privacy unless EveryMind has verified them.",
        "intervention_ids": ["confidentiality_explained", "accessibility_question_pack", "myth_vs_reality"],
    },
    "Psychological comfort": {
        "established": "The survey does not measure comfort, embarrassment, or doubt about whether something is 'serious enough'.",
        "unknown": "Whether people hold back because they feel their struggles are 'not a real crisis'.",
        "design_choices": [
            "Make participation opt-in with no personal disclosure.",
            "Use supportive scenarios.",
            "Explain what contacting 988 can involve.",
        ],
        "future_questions": [
            "Optional: 'How comfortable did you feel taking part in today's training?'",
            "Optional: 'How confident would you feel contacting 988 if you needed to?'",
        ],
        "interpretation": "Do not infer trauma or mental-health history.",
        "intervention_ids": ["low_pressure_participation", "help_seeking_confidence", "crisis_scenarios"],
    },
}

DIMENSION_NAMES = list(DIMENSIONS.keys())


# ---------------------------------------------------------------------------
# 4. SMALL HELPERS
# ---------------------------------------------------------------------------
def _num(value):
    """Return value as a number, or None if it is missing/invalid (never turns missing into 0)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return int(number) if number == int(number) else number


def _status_label(status):
    """Human-friendly label for a finding status."""
    status = str(status or "unknown").lower()
    if status == "synthetic":
        return "SYNTHETIC (demo only)"
    return status.replace("_", " ").capitalize()


def normalize_finding(finding, index=0):
    """
    Make sure a finding has every standard field. Missing fields become None / [] / {}.
    Non-dict input becomes an empty 'unknown' finding (it will show as Needs review).
    """
    if not isinstance(finding, dict):
        finding = {}
    limitations = finding.get("limitations")
    if isinstance(limitations, str):
        limitations = [limitations]
    elif not isinstance(limitations, (list, tuple)):
        limitations = []
    evidence = finding.get("evidence")
    return {
        "id": str(finding.get("id") or "finding_%d" % (index + 1)),
        "source": str(finding.get("source") or "unknown source"),
        "type": finding.get("type"),
        "title": str(finding.get("title") or "Untitled finding"),
        "description": str(finding.get("description") or ""),
        "count": _num(finding.get("count")),
        "denominator": _num(finding.get("denominator")),
        "percentage": _num(finding.get("percentage")),
        "limitations": [str(x) for x in limitations],
        "evidence": evidence if isinstance(evidence, dict) else {},
        "status": str(finding.get("status") or "unknown"),
    }


def evidence_text(finding):
    """
    One plain sentence describing the evidence behind a finding.
    Uses ONLY values that exist; missing values are described as 'not available'.
    """
    f = normalize_finding(finding)
    count, denom, pct = f["count"], f["denominator"], f["percentage"]
    if pct is None and count is not None and denom:
        pct = round(100.0 * count / denom, 1)       # simple arithmetic, not an invented value
    if count is not None and denom is not None:
        numbers = "%s of %s responses" % (count, denom)
        if pct is not None:
            numbers += " (%.1f%%)" % pct
    elif count is not None:
        numbers = "%s responses (denominator not available)" % count
    else:
        numbers = "counts not available"
    text = "%s: %s. Source: %s. Status: %s." % (f["title"], numbers, f["source"], _status_label(f["status"]))
    if f["limitations"]:
        text += " Limitations: " + "; ".join(f["limitations"]) + "."
    return text


def get_intervention(intervention_id):
    """Return a COPY of one intervention (with its id added), or None if unknown."""
    item = INTERVENTIONS.get(intervention_id)
    if item is None:
        return None
    result = copy.deepcopy(item)
    result["id"] = intervention_id
    return result


def list_interventions():
    """Return copies of all interventions in catalog order."""
    return [get_intervention(i) for i in CATALOG_ORDER]


def get_dimension_info(name):
    """Return a copy of the Inclusive Action Lens info for one dimension (or None)."""
    info = DIMENSIONS.get(name)
    return copy.deepcopy(info) if info else None


# ---------------------------------------------------------------------------
# 5. MAIN FUNCTION #1: recommend_interventions
# ---------------------------------------------------------------------------
def recommend_interventions(findings):
    """
    Match findings to candidate interventions.

    Input : list of finding dicts (see sample_findings.FINDING_FIELDS). Can be empty or None.
    Output: a dict with
        "recommendations": de-duplicated list of interventions. Each has an extra key
                           "triggered_by" = list of {id, title, type, role, note} showing which
                           findings triggered it (role = 'first' or 'alternative').
        "by_finding": {finding_id: {"finding", "status", "intervention_ids", "message"}}
                      status is "matched" or "needs_review". At most 3 ids per finding.
        "needs_review": list of findings with a missing/unknown type (no advice invented).
    """
    result = {"recommendations": [], "by_finding": {}, "needs_review": []}
    if not findings:
        return result

    by_id = {}      # intervention id -> recommendation dict (for de-duplication)
    for index, raw in enumerate(findings):
        finding = normalize_finding(raw, index)
        # Make finding ids unique if two findings share an id.
        base_id, n = finding["id"], 2
        while finding["id"] in result["by_finding"]:
            finding["id"] = "%s_%d" % (base_id, n)
            n += 1

        ids = FINDING_TYPE_MAP.get(finding["type"]) if isinstance(finding["type"], str) else None
        if not ids:
            # Unknown or missing type -> safe state, no invented recommendation.
            result["by_finding"][finding["id"]] = {
                "finding": finding, "status": "needs_review", "intervention_ids": [],
                "message": "Needs review: this finding type is missing or not recognized, so no "
                           "recommendation is suggested. Check the finding with the team.",
            }
            result["needs_review"].append(finding)
            continue

        ids = ids[:3]
        result["by_finding"][finding["id"]] = {
            "finding": finding, "status": "matched", "intervention_ids": list(ids), "message": "",
        }
        for position, intervention_id in enumerate(ids):
            if intervention_id not in by_id:
                rec = get_intervention(intervention_id)
                rec["triggered_by"] = []
                by_id[intervention_id] = rec
                result["recommendations"].append(rec)
            by_id[intervention_id]["triggered_by"].append({
                "id": finding["id"],
                "title": finding["title"],
                "type": finding["type"],
                "role": "first" if position == 0 else "alternative",
                "note": PAIR_NOTES.get((finding["type"], intervention_id), ""),
            })
    return result


# ---------------------------------------------------------------------------
# 6. MAIN FUNCTION #2: build_action_plan
# ---------------------------------------------------------------------------
def build_action_plan(findings, selected_ids):
    """
    Build the action plan for the chosen interventions.

    Input : findings list, and selected_ids (list of intervention ids).
    Output: list of dicts (one per valid selected id, no duplicates) with:
        id, title, why, current_evidence, proposed_change, future_measurement,
        decision_rule, steps, owner, effort, effort_note, checkin, unanswered,
        caveats, triggered_by (list of finding titles), dimensions
    Unknown ids are skipped. Empty selection -> empty list.
    """
    if not selected_ids:
        return []
    if isinstance(selected_ids, str):
        selected_ids = [selected_ids]

    recs = recommend_interventions(findings)
    triggered = {rec["id"]: rec["triggered_by"] for rec in recs["recommendations"]}
    finding_lookup = {f["id"]: f for f in (v["finding"] for v in recs["by_finding"].values())}

    plan, seen = [], set()
    for intervention_id in selected_ids:
        if intervention_id in seen:
            continue
        item = get_intervention(intervention_id)
        if item is None:
            continue
        seen.add(intervention_id)

        triggers = triggered.get(intervention_id, [])
        if triggers:
            lines = [evidence_text(finding_lookup[t["id"]]) for t in triggers if t["id"] in finding_lookup]
            current_evidence = " | ".join(lines)
            notes = [t["note"] for t in triggers if t["note"]]
        else:
            current_evidence = "No current finding triggers this action (it was added manually)."
            notes = []

        caveats = list(item["caveats"]) + notes
        for t in triggers:
            f = finding_lookup.get(t["id"])
            if f:
                for limit in f["limitations"]:
                    if limit not in caveats:
                        caveats.append(limit)

        plan.append({
            "id": intervention_id,
            "title": item["title"],
            "kind": item["kind"],
            "why": item["why"],
            "current_evidence": current_evidence,
            "proposed_change": item["summary"],
            "future_measurement": item["metric"],
            "decision_rule": item["change_mind"],
            "steps": item["steps"],
            "owner": item["owner"],
            "effort": item["effort"],
            "effort_note": "Planning estimate only, not a proven impact score.",
            "checkin": item["checkin"],
            "unanswered": item["unanswered"],
            "caveats": caveats,
            "triggered_by": [t["title"] for t in triggers],
            "dimensions": [name for name, d in DIMENSIONS.items() if intervention_id in d["intervention_ids"]],
        })
    return plan