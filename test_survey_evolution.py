"""End-to-end synthetic XLSX tests: original form vs. revised questionnaire.

No participant records are used. These tests write two different fake Excel
workbooks in memory and run each through the actual upload pipeline.
"""
from __future__ import annotations

from io import BytesIO
import unittest

import pandas as pd

from cleaning import EXPECTED_COLUMNS
from pipeline import run_pipeline
from person4.survey_designer import analyze_survey, question_bank
from survey_evidence import team_survey_findings


def fictional_workbook(*, revised=False) -> BytesIO:
    records = []
    for index in range(4):
        record = {column: "" for column in EXPECTED_COLUMNS}
        record.update({
            "id": f"FICTIONAL-ROW-{index + 1}",
            "start_time": "2026-11-01 09:00:00",
            "completion_time": "2026-11-01 09:10:00",
            "training_date": "2026-11-01",
            "language": "English",
            "participant_type": "Student",
            "county": "Montgomery",
            "before_identify": "Disagree",
            "before_describe": "Disagree",
            "before_when": "Disagree",
            "after_identify": "Agree",
            "after_describe": "Strongly agree",
            "after_when": "Strongly agree",
            "presenter_engagement": "Agree",
            "presenter_expertise": "Agree",
            "training_organization": "Agree",
            "recommend_training": 9,
            "willingness_to_call": (
                [2, 4, 5, 3][index] if not revised
                else [8, 9, 10, 9][index]
            ),
            "valuable_feedback": "I learned when 988 can help.",
            "improvement_feedback": (
                ["Please clarify privacy and confidentiality",
                 "Can the phone call be recorded?",
                 "More information about privacy policies",
                 "What happens during a call?"][index]
                if not revised
                else ["More interactive activities",
                      "Practice with role-play scenarios",
                      "More visuals and videos",
                      "More examples"][index]
            ),
        })
        records.append(record)
    frame = pd.DataFrame(records, columns=EXPECTED_COLUMNS)
    if revised:
        by_id = {q["id"]: q["question"] for q in question_bank}
        frame[by_id["COM01"]] = ["Text message", "Phone call", "Online chat", "Text message"]
        frame[by_id["TRU01"]] = ["Very clearly"] * len(frame)
        frame["What is your favorite style of music?"] = ["Jazz"] * len(frame)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Survey Data", index=False)
    output.seek(0)
    return output


def analyze_fictional(*, revised=False):
    pipeline = run_pipeline(fictional_workbook(revised=revised))
    # Cleaned data retains newly added headers alongside all original metrics.
    evidence = team_survey_findings(pipeline.clean_df)
    report = analyze_survey(pipeline.clean_df, external_findings=evidence)
    return pipeline, report


class EvolvingSurveyWorkbookTests(unittest.TestCase):
    def test_original_form_has_real_measurement_gaps(self):
        pipeline, report = analyze_fictional(revised=False)
        self.assertEqual(len(pipeline.clean_df), 4)
        self.assertEqual(pipeline.summary["overview"]["willingness_valid_n"], 4)
        self.assertEqual(report["recognized_question_ids"], [])
        self.assertIn("COM01", report["recommendations"]["question_id"].tolist())
        self.assertIn("TRU01", report["recommendations"]["question_id"].tolist())
        self.assertTrue(any(
            f["type"] == "call_only_measure" for f in report["findings"]
        ))
        self.assertTrue(any(
            f["type"] == "knowledge_willingness_gap" for f in report["findings"]
        ))
        self.assertTrue(any(
            f["type"] == "feedback_privacy_questions" for f in report["findings"]
        ))
        com_row = report["coverage"].set_index("dimension").loc["Communication"]
        self.assertEqual(com_row["coverage"], "Partially measured")

    def test_revised_form_changes_coverage_and_recommendations(self):
        pipeline, report = analyze_fictional(revised=True)
        self.assertEqual(len(pipeline.raw_df.columns), 23)
        self.assertEqual(len(pipeline.clean_df), 4)
        self.assertEqual(pipeline.summary["overview"]["willingness_valid_n"], 4)
        self.assertEqual(pipeline.summary["overview"]["survey_rows"], 4)
        self.assertEqual(
            int(pipeline.audit["schema"]["supplemental_question_count"]), 3
        )
        self.assertIn("COM01", report["recognized_question_ids"])
        self.assertIn("TRU01", report["recognized_question_ids"])
        self.assertNotIn("COM01", report["recommendations"]["question_id"].tolist())
        self.assertNotIn("TRU01", report["recommendations"]["question_id"].tolist())
        dimensions = report["coverage"].set_index("dimension")
        self.assertEqual(dimensions.loc["Communication", "coverage"],
                         "Directly measured")
        self.assertEqual(dimensions.loc["Institutional Trust", "coverage"],
                         "Directly measured")
        self.assertFalse(any(
            f["type"] == "call_only_measure" for f in report["findings"]
        ))
        self.assertFalse(any(
            f["type"] == "knowledge_willingness_gap" for f in report["findings"]
        ))
        self.assertFalse(any(
            f["type"] == "feedback_privacy_questions" for f in report["findings"]
        ))
        self.assertEqual(len(report["unclassified_question_columns"]), 1)
        self.assertIn("favorite style of music",
                      report["unclassified_question_columns"][0])

    def test_unknown_extra_columns_do_not_break_existing_analysis(self):
        original, report_a = analyze_fictional(revised=False)
        revised, report_b = analyze_fictional(revised=True)
        self.assertEqual(
            original.summary["knowledge"]["topics"]["Know when to use 988"]["n"],
            revised.summary["knowledge"]["topics"]["Know when to use 988"]["n"],
        )
        self.assertNotEqual(report_a["recognized_question_ids"],
                            report_b["recognized_question_ids"])
        self.assertNotEqual(
            set(report_a["recommendations"]["question_id"]),
            set(report_b["recommendations"]["question_id"]),
        )

    def test_required_original_columns_remain_mandatory(self):
        frame = pd.DataFrame({"id": [1], "An added question?": ["Yes"]})
        output = BytesIO()
        frame.to_excel(output, sheet_name="Survey Data", index=False)
        output.seek(0)
        with self.assertRaisesRegex(ValueError, "Missing columns"):
            run_pipeline(output)


if __name__ == "__main__":
    unittest.main()
