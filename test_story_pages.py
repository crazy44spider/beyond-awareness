"""Safe unit tests of story-facing transformations; no participant data used."""
import unittest

import pandas as pd

from story_pages import _pct, _private_preview, _pick_themes
from story_theme import esc


class StoryPresentationTests(unittest.TestCase):
    def test_percentage_handles_missing(self):
        self.assertEqual(_pct(None), "Unavailable")
        self.assertEqual(_pct(0.25), "25%")

    def test_theme_filter_only_changes_display(self):
        original = pd.Series(
            [30, 20, 10, 5],
            index=["Other", "More depth / content / practice",
                   "Interactive / hands-on activities", "Too brief to code"],
        )
        filtered = _pick_themes(original)
        self.assertEqual(
            list(filtered.index),
            ["More depth / content / practice", "Interactive / hands-on activities"],
        )
        self.assertEqual(len(original), 4)

    def test_private_comment_preview_masks_common_identifiers(self):
        text = "Contact someone@example.org, (301) 555-0199 or https://example.org/about"
        masked = _private_preview(text)
        self.assertNotIn("someone@example.org", masked)
        self.assertNotIn("555-0199", masked)
        self.assertNotIn("https://example.org", masked)
        self.assertIn("[email]", masked)
        self.assertIn("[phone]", masked)

    def test_html_is_escaped_in_custom_cards(self):
        self.assertEqual(esc("<script>"), "&lt;script&gt;")


if __name__ == "__main__":
    unittest.main()
