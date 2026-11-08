"""Regression tests for Person 3's import-safe, upload-compatible analyzer."""
import unittest
import pandas as pd
from feedback_analyzer import analyze_feedback


class FeedbackIntegrationTests(unittest.TestCase):
    def test_two_different_uploads_produce_different_results(self):
        first = pd.DataFrame({
            "id": [1, 2],
            "valuable_feedback": ["I learned when to call 988", "988 is available 24/7"],
            "improvement_feedback": ["More interactive activities", "More videos"],
        })
        second = pd.DataFrame({
            "id": [1],
            "valuable_feedback": ["How to help my friends"],
            "improvement_feedback": ["More information about privacy"],
        })
        a = analyze_feedback(first)
        b = analyze_feedback(second)
        self.assertEqual(len(a["data"]), 2)
        self.assertEqual(len(b["data"]), 1)
        self.assertIn("Interactive / hands-on activities", a["improve_counts"].index)
        self.assertIn("Privacy and confidentiality", b["improve_counts"].index)
        self.assertNotIn("Interactive / hands-on activities", b["improve_counts"].index)
        self.assertNotIn("learned_themes", first.columns)

    def test_missing_columns_have_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Missing required survey columns"):
            analyze_feedback(pd.DataFrame({"id": [1]}))

    def test_no_comments(self):
        data = pd.DataFrame({
            "id": [3],
            "valuable_feedback": [None],
            "improvement_feedback": [None],
        })
        result = analyze_feedback(data)
        self.assertTrue(result["learned_counts"].empty)
        self.assertTrue(result["improve_counts"].empty)


if __name__ == "__main__":
    unittest.main()
