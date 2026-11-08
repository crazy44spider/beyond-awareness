"""Release-level regression tests, entirely fictional: all core pipelines + PDFs.

Includes the ORIGINAL survey's actual Excel heading schema, a revised workbook
with extra survey items, filtered data, response-driven recommendations,
Participant Voices summaries, and both PDF generation pathways.
"""
from __future__ import annotations

from io import BytesIO
import json
import unittest

import pandas as pd

from cleaning import SOURCE_HEADERS, EXPECTED_COLUMNS, load_survey
from pipeline import build_summary, filter_survey, run_pipeline
from team_integration import build_action_findings, to_person5_metrics
from intervention_planner import get_intervention, recommend_interventions
from report_generator import generate_report
from person4.survey_designer import analyze_survey
from survey_evidence import team_survey_findings
from test_survey_evolution import fictional_workbook


def original_header_workbook() -> BytesIO:
    """One fully fictional row with the 20 original, long Excel headings."""
    fields = [
        "FAKE-ORIGINAL-001",
        "2026-11-01 09:00:00", "2026-11-01 09:12:00",
        "English", "Student", "2026-11-01", "Montgomery",
        "Strongly agree", "Strongly agree", "Agree",
        "Disagree", "Disagree", "Disagree",
        "Agree", "Agree", "Agree", 10, 8,
        "I learned how 988 works.", "More interactive examples would help.",
    ]
    frame = pd.DataFrame([fields], columns=SOURCE_HEADERS)
    content = BytesIO()
    with pd.ExcelWriter(content, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Survey Data", index=False)
    content.seek(0)
    return content


class ReleaseAuditTests(unittest.TestCase):
    def test_original_long_header_excel_upload(self):
        result = run_pipeline(original_header_workbook())
        self.assertEqual(result.audit["schema"]["supplemental_question_count"], 0)
        self.assertEqual(len(result.clean_df), 1)
        self.assertEqual(result.clean_df["id"].iloc[0], "FAKE-ORIGINAL-001")
        self.assertEqual(result.summary["overview"]["survey_rows"], 1)
        self.assertEqual(result.summary["overview"]["willingness_valid_n"], 1)

    def test_revision_preserves_core_numerical_analysis_and_questions(self):
        original = run_pipeline(fictional_workbook(revised=False))
        revised = run_pipeline(fictional_workbook(revised=True))
        self.assertEqual(len(original.raw_df.columns), len(EXPECTED_COLUMNS))
        self.assertEqual(len(revised.raw_df.columns), len(EXPECTED_COLUMNS) + 3)
        self.assertEqual(
            original.summary["knowledge"]["topics"]["Know when to use 988"]["n"],
            revised.summary["knowledge"]["topics"]["Know when to use 988"]["n"],
        )
        orig = analyze_survey(
            original.clean_df,
            external_findings=team_survey_findings(original.clean_df),
        )
        new = analyze_survey(
            revised.clean_df,
            external_findings=team_survey_findings(revised.clean_df),
        )
        self.assertEqual(orig["recognized_question_ids"], [])
        self.assertIn("COM01", new["recognized_question_ids"])
        self.assertIn("TRU01", new["recognized_question_ids"])
        self.assertNotIn("COM01", set(new["recommendations"]["question_id"]))
        self.assertNotIn("TRU01", set(new["recommendations"]["question_id"]))

    def test_filtering_can_leave_no_responses_and_empty_summary(self):
        result = run_pipeline(fictional_workbook(revised=False))
        filtered = filter_survey(result.clean_df, languages=["Spanish"])
        self.assertTrue(filtered.empty)
        summary = build_summary(filtered)
        self.assertEqual(summary["overview"]["survey_rows"], 0)
        self.assertEqual(summary["overview"]["willingness_valid_n"], 0)

        selected = filter_survey(result.clean_df, counties=["Montgomery"])
        self.assertEqual(len(selected), len(result.clean_df))
        json.dumps(build_summary(selected), allow_nan=False)

    def test_original_and_revised_pdf_coverage_matches_questionnaire(self):
        first = run_pipeline(fictional_workbook(revised=False))
        second = run_pipeline(fictional_workbook(revised=True))
        a = to_person5_metrics(first.clean_df, first.summary, "Synthetic uploaded survey")
        b = to_person5_metrics(second.clean_df, second.summary, "Synthetic uploaded survey")
        self.assertEqual(a["status"], "synthetic")
        self.assertEqual(b["status"], "synthetic")
        self.assertFalse(a["responses_verified"])
        self.assertEqual(a["n_responses"], 4)
        self.assertEqual(b["n_responses"], 4)
        self.assertEqual(a["dimension_status"]["Communication access"], "Partially measured")
        self.assertEqual(b["dimension_status"]["Communication access"], "Measured (added question)")
        self.assertEqual(b["dimension_status"]["Institutional trust"], "Measured (added question)")
        self.assertIn("0 of 4", b["knowledge_call_relationship"]["summary"])
        self.assertIn("4 of 4", a["knowledge_call_relationship"]["summary"])
        self.assertTrue(a["themes"])
        self.assertTrue(all(t["validated"] is False for t in a["themes"]))
        self.assertNotEqual(
            [t["theme"] for t in a["themes"]],
            [t["theme"] for t in b["themes"]],
        )

    def test_generate_real_pdf_with_findings_and_no_actions(self):
        result = run_pipeline(fictional_workbook(revised=False))
        metrics = to_person5_metrics(result.clean_df, result.summary, "Synthetic uploaded survey")
        findings = build_action_findings(result.clean_df)
        pdf = generate_report(metrics, findings, selected_interventions=[])
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", pdf[-128:])
        self.assertGreater(len(pdf), 5000)

    def test_generate_real_pdf_with_selected_intervention(self):
        result = run_pipeline(fictional_workbook(revised=False))
        metrics = to_person5_metrics(result.clean_df, result.summary, "Synthetic uploaded survey")
        findings = build_action_findings(result.clean_df)
        candidates = recommend_interventions(findings)["recommendations"]
        self.assertTrue(candidates)
        selection = [candidates[0]["id"]]
        self.assertIsNotNone(get_intervention(selection[0]))
        with_action = generate_report(metrics, findings, selected_interventions=selection)
        without_action = generate_report(metrics, findings, selected_interventions=[])
        self.assertTrue(with_action.startswith(b"%PDF-"))
        self.assertGreater(len(with_action), len(without_action) // 2)
        self.assertNotEqual(with_action, without_action)


if __name__ == "__main__":
    unittest.main()
