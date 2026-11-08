"""Small synthetic smoke tests for the team integration layer.

Run from the repo root:
    python -m unittest test_team_integration.py

No raw EveryMind participant data is used by these tests.
"""
import unittest

import pandas as pd

from team_integration import build_action_findings, to_person5_metrics
from report_generator import generate_report


class TeamIntegrationSmokeTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "before_identify": [2, 3, 1],
            "after_identify": [4, 4, 3],
            "before_describe": [2, 2, 1],
            "after_describe": [4, 4, 3],
            "before_when": [2, 3, 2],
            "after_when": [5, 4, 3],
            "willingness_to_call": [4, None, None],
            "valuable_feedback": ["I learned when to call", "", "988 is available"],
            "improvement_feedback": ["Please explain privacy", "", "More videos"],
            "language": ["English", "English", "Spanish"],
            "training_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        })

    def test_findings_are_aggregate_and_recognized(self):
        findings = build_action_findings(self.df)
        by_type = {f["type"]: f for f in findings}
        self.assertIn("communication_measurement_gap", by_type)
        self.assertIn("low_call_intent_response_rate", by_type)
        self.assertIn("knowledge_action_gap", by_type)
        self.assertEqual(by_type["knowledge_action_gap"]["count"], 1)
        self.assertEqual(by_type["knowledge_action_gap"]["denominator"], 1)
        # Keyword-only privacy mentions are not reported as a validated concern.
        self.assertNotIn("privacy_feedback_concern", by_type)

    def test_report_schema_and_pdf(self):
        summary = {
            "overview": {"survey_rows": 3, "willingness_valid_n": 1},
            "knowledge": {"topics": {
                "Know when to use 988": {
                    "n": 3, "before_mean": 2.3, "after_mean": 4.0
                }
            }},
        }
        metrics = to_person5_metrics(self.df, summary, "Synthetic demo")
        self.assertEqual(metrics["status"], "synthetic")
        self.assertEqual(metrics["call_intent"]["n_answered"], 1)
        self.assertEqual(metrics["knowledge"][0]["n_paired"], 3)
        pdf = generate_report(metrics, build_action_findings(self.df), ["contact_method"])
        self.assertTrue(pdf.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
