"""Streamlit UI route smoke tests using the built-in in-process AppTest runner.

The complete synthetic dataset is used; no survey data or browser dependencies.
"""
import unittest

from streamlit.testing.v1 import AppTest


class NavigationSmokeTests(unittest.TestCase):
    def test_all_eight_pages_render_with_synthetic_data(self):
        app = AppTest.from_file("app.py", default_timeout=60)
        app.session_state["source_mode_v2"] = "Synthetic test data"
        pages = [
            "Overview", "Training Outcomes", "Gap Detector",
            "Participant Voices", "Survey Designer",
            "Intervention Planner", "Reports", "Detailed Analysis",
        ]
        for page in pages:
            with self.subTest(page=page):
                app.session_state["workspace_page"] = page
                app.run(timeout=60)
                errors = [str(item.message) for item in app.exception]
                self.assertEqual(errors, [], f"{page} failed to render: {errors}")
                self.assertEqual(app.session_state["workspace_page"], page)


if __name__ == "__main__":
    unittest.main()
