"""Transparent adapters from Person 2 and Person 3 to Person 4's question rules.

Keep teammate analysis algorithms intact. These findings indicate WHAT to
measure next; keyword themes and statistical patterns do not establish WHY.
"""
from __future__ import annotations

import re
import pandas as pd

from person2.gap_detector import detect_findings, knowledge_vs_willingness
from feedback_analyzer import analyze_feedback
from person4.survey_designer import make_finding


THEME_TO_FINDING = {
    "Privacy and confidentiality": "feedback_privacy_questions",
    "Handling difficult situations / understanding crisis": "feedback_crisis_questions",
    "What calls are like / real stories": "feedback_call_experience_questions",
    "Local resources / relevance to the county": "feedback_local_relevance_questions",
}


def team_survey_findings(clean_df: pd.DataFrame, feedback: dict | None = None) -> list[dict]:
    """Return normalized findings on the SAME filtered set of survey rows."""
    if clean_df.empty:
        return []

    results = []

    # Preserve the full Person 2 detector, including its caveats.
    person2 = detect_findings(clean_df)
    paired = knowledge_vs_willingness(clean_df)
    for index, finding in enumerate(person2):
        raw_type = finding["type"]
        finding_type = f"person2_{raw_type}_{index}"
        if raw_type == "knowledge_willingness":
            if int(paired["gap_count"]) > 0:
                finding_type = "knowledge_willingness_gap"
            else:
                finding_type = "person2_no_knowledge_willingness_gap"
        results.append(make_finding(
            finding_type=finding_type,
            title=finding["title"],
            description=str(finding["evidence"]),
            source="person2_gap_detector",
            count=int(paired["gap_count"]) if raw_type == "knowledge_willingness" else None,
            denominator=int(paired["complete_case_n"]) if raw_type == "knowledge_willingness" else None,
            limitations=[str(finding["limitation"])],
            evidence={"detector_type": raw_type, "rule": "person2_original"},
        ))

    # Person 3 performs the existing comment classification. Do not equate a
    # theme mention with a confirmed barrier, nor read any feedback as proof of
    # demographic needs. Each theme contributes descriptive keyword evidence.
    if feedback is None:
        feedback = analyze_feedback(clean_df)
    comments = feedback["data"]
    valid_n = int(comments["improve_en"].notna().sum())
    for name, count in feedback["improve_counts"].items():
        n = int(count)
        if n <= 0:
            continue
        key = THEME_TO_FINDING.get(str(name))
        if key is None:
            slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
            key = f"person3_theme_{slug}"
        results.append(make_finding(
            finding_type=key,
            title=f'Participant feedback mentioned: {name}',
            description=(
                f"{n:,} coded theme mention(s) among "
                f"{valid_n:,} usable improvement comments. "
                "A response can match more than one theme."
            ),
            source="person3_feedback_themes",
            count=n,
            denominator=valid_n if valid_n else None,
            limitations=[
                "Keyword classification is preliminary, not verified respondent intent.",
                "A mention does not prove that a person experienced a barrier.",
            ],
            evidence={"theme": str(name), "method": "person3_original_keyword_coding"},
        ))
    return results
