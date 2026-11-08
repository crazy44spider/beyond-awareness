"""Safe unit tests of story-facing transformations; no participant data used."""
import unittest
from unittest.mock import patch

import plotly.graph_objects as go

import pandas as pd

from story_pages import _pct, _private_preview, _pick_themes, _lock_figure, PLOT_CONFIG
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

    def test_figure_is_not_zoomable_draggable_or_hideable(self):
        fig = go.Figure()
        fig.add_bar(name="Before", x=[2, 3], y=["A", "B"])
        fig.add_bar(name="Current", x=[4, 5], y=["A", "B"])
        self.assertIs(_lock_figure(fig), fig)
        self.assertIs(fig.layout.dragmode, False)
        self.assertEqual(fig.layout.clickmode, "none")
        self.assertIs(fig.layout.xaxis.fixedrange, True)
        self.assertIs(fig.layout.yaxis.fixedrange, True)
        self.assertIs(fig.layout.legend.itemclick, False)
        self.assertIs(fig.layout.legend.itemdoubleclick, False)
        self.assertIs(PLOT_CONFIG["scrollZoom"], False)
        self.assertIs(PLOT_CONFIG["doubleClick"], False)
        self.assertIs(PLOT_CONFIG["editable"], False)
        self.assertNotIn("staticPlot", PLOT_CONFIG)  # Keep hover readouts.

    def test_legacy_charts_are_locked_too(self):
        from dashboard import _chart
        fig = go.Figure(go.Bar(x=[1, 2], y=[5, 8]))
        with patch("dashboard.st.plotly_chart") as chart:
            _chart(fig, "unit_locked", height=320)
            self.assertTrue(chart.called)
            options = chart.call_args.kwargs["config"]
            self.assertIs(options["scrollZoom"], False)
            self.assertIs(options["doubleClick"], False)
            self.assertIs(fig.layout.xaxis.fixedrange, True)
            self.assertIs(fig.layout.yaxis.fixedrange, True)
            self.assertIs(fig.layout.dragmode, False)

    def test_html_is_escaped_in_custom_cards(self):
        self.assertEqual(esc("<script>"), "&lt;script&gt;")


if __name__ == "__main__":
    unittest.main()
