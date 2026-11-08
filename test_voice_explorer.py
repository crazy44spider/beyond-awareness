"""Synthetic tests for the live Participant Voices HTML/SVG explorer.

The browser event handlers are tested as authored HTML; automatic Python
checks cannot substitute for a final visual hover check in the browser.
"""
import json
import re
import unittest

import pandas as pd

from feedback_analyzer import analyze_feedback
from story_pages import _cached_voice_analysis, _pick_themes, _private_preview, _voice_entries
from voice_explorer import _safe_payload_json, make_voice_explorer_html


def fake_feedback(comments):
    return pd.DataFrame({
        "id": list(range(1, len(comments) + 1)),
        "valuable_feedback": ["I learned when to call 988."] * len(comments),
        "improvement_feedback": comments,
        "county": ["Montgomery"] * len(comments),
        "participant_type": ["Student"] * len(comments),
    })


class VoiceExplorerTests(unittest.TestCase):
    def setUp(self):
        self.privacy = fake_feedback([
            "Can you explain privacy and confidentiality?",
            "How do they handle recorded calls?",
            "What happens during a call?",
            "Could you explain confidentiality again?",
        ])
        self.practice = fake_feedback([
            "Please give us more interactive activities.",
            "More hands-on scenarios and role-play.",
            "More practice with scenarios.",
            "Please add a video.",
        ])

    def test_different_survey_uploads_have_different_themes(self):
        a = analyze_feedback(self.privacy)
        b = analyze_feedback(self.practice)
        self.assertIn("Privacy and confidentiality", a["improve_counts"])
        self.assertNotIn("Privacy and confidentiality", b["improve_counts"])
        self.assertIn("Interactive / hands-on activities", b["improve_counts"])

    def test_example_comments_are_limited_and_masked(self):
        data = fake_feedback([
            f"Please discuss privacy with me{i}@example.org"
            for i in range(12)
        ])
        result = analyze_feedback(data)
        counts = _pick_themes(result["improve_counts"], max_items=7)
        entries = _voice_entries(
            result, counts, tag_field="improve_themes", text_field="improve_en",
        )
        selected = next(
            item for item in entries if item["label"] == "Privacy and confidentiality"
        )
        self.assertEqual(selected["count"], 12)
        self.assertLessEqual(len(selected["comments"]), 5)
        self.assertNotIn("@example.org", " ".join(selected["comments"]))

    def test_duplicate_comments_do_not_fill_all_preview_cards(self):
        data = fake_feedback(["Could you clarify privacy?"] * 5)
        result = analyze_feedback(data)
        entries = _voice_entries(
            result, _pick_themes(result["improve_counts"]),
            tag_field="improve_themes", text_field="improve_en",
        )
        selected = next(
            item for item in entries if item["label"] == "Privacy and confidentiality"
        )
        self.assertEqual(selected["count"], 5)
        self.assertEqual(len(selected["comments"]), 1)

    def test_payload_escapes_script_breakouts(self):
        attack = "</script><script>window.evil=true</script>"
        payload = _safe_payload_json({"comment": attack, "label": "A & B"})
        self.assertNotIn(attack, payload)
        self.assertNotIn("</script><script>", payload)
        self.assertIn("\\u003c", payload)
        self.assertEqual(json.loads(payload)["comment"], attack)

    def test_hover_and_keyboard_handlers_update_selection_in_place(self):
        html = make_voice_explorer_html([
            {"label": "Privacy and confidentiality", "count": 2,
             "comments": ["Can you explain privacy?", "What happens to call records?"]},
            {"label": "Interactive / hands-on activities", "count": 1,
             "comments": ["Can we practice with a scenario?"]},
        ], category="What to improve", comment_count=3)
        self.assertIn('addEventListener("mouseenter",()=>show(i))', html)
        self.assertIn('addEventListener("mouseleave",()=>show(picked))', html)
        self.assertIn('addEventListener("click",()=>select(i))', html)
        self.assertIn('event.key==="Enter"', html)
        self.assertIn("commentList.replaceChildren()", html)
        self.assertIn("block.textContent", html)
        self.assertIn("distance = active ? 4 : 0", html)
        self.assertNotIn("streamlit-rerun", html)

    def test_cache_tracks_different_filtered_datasets(self):
        # Streamlit caches this pure function based on the input DataFrame.
        first = _cached_voice_analysis(self.privacy)
        second = _cached_voice_analysis(self.practice)
        self.assertIn("Privacy and confidentiality", first["improve_counts"].index)
        self.assertIn("Interactive / hands-on activities", second["improve_counts"].index)
        self.assertNotIn("Privacy and confidentiality", second["improve_counts"].index)

    def test_existing_masking_still_applies(self):
        masked = _private_preview("Talk to test@example.org at (301) 555-0199.")
        self.assertIn("[email]", masked)
        self.assertIn("[phone]", masked)


if __name__ == "__main__":
    unittest.main()
