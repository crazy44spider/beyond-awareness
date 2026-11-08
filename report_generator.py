"""
report_generator.py  (Person 5)
===============================
Builds the "Improvement Brief" PDF and returns it as BYTES.

Main function (no streamlit needed):
    generate_report(metrics, findings, selected_interventions) -> bytes

    metrics                  dict of numbers (ALL keys optional; missing -> "Not available").
                             See sample_findings.SYNTHETIC_METRICS for every key.
    findings                 list of finding dicts (same fields as sample_findings.FINDING_FIELDS)
    selected_interventions   list of intervention ids (strings) OR dicts that have an "id" key

Rules: no row-level comments in the PDF by default, no causal claims,
no invented numbers, and a big SYNTHETIC banner whenever demo data is used.

Requires:  pip install reportlab
"""

import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

from intervention_planner import DIMENSIONS, DIMENSION_NAMES, build_action_plan, normalize_finding, _num

# ---------------------------------------------------------------------------
# Colors from the brief (change here to restyle the whole PDF)
# ---------------------------------------------------------------------------
PURPLE = colors.HexColor("#4B2E83")
LAVENDER = colors.HexColor("#EDE7F6")
TEAL = colors.HexColor("#148A83")
TEXT = colors.HexColor("#222222")
GRAY = colors.HexColor("#666666")

DEMO_BANNER = "SYNTHETIC DEMONSTRATION - NOT EVERYMIND RESULTS"
NA = "Not available"

# ---------------------------------------------------------------------------
# Text styles
# ---------------------------------------------------------------------------
S_TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=26, leading=31, textColor=PURPLE, spaceAfter=6)
S_SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=13, leading=17, textColor=TEAL, spaceAfter=14)
S_H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=PURPLE, spaceBefore=6, spaceAfter=6, keepWithNext=1)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=4, keepWithNext=1)
S_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14, textColor=TEXT, spaceAfter=5)
S_SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=11, textColor=TEXT)
S_NOTE = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=GRAY, spaceAfter=6)
S_HEAD = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white)
S_BANNER = ParagraphStyle("banner", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.white, alignment=1)


def _p(text, style=S_BODY):
    """Make a Paragraph from plain text. Escapes < > & so odd characters cannot break the PDF."""
    text = "" if text is None else str(text)
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _bullets(items, style=S_BODY):
    """List of bullet Paragraphs (empty list -> one 'Not available' line)."""
    if not items:
        return [_p("- " + NA, style)]
    return [_p("- " + str(i), style) for i in items]


def _table(rows, col_widths, header=True):
    """Build a consistently styled table. rows = list of lists of strings or flowables."""
    data = []
    for r_index, row in enumerate(rows):
        new_row = []
        for cell in row:
            if isinstance(cell, str):
                cell = _p(cell, S_HEAD if (header and r_index == 0) else S_SMALL)
            new_row.append(cell)
        data.append(new_row)
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFC4E6")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), PURPLE))
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), LAVENDER))
    table.setStyle(TableStyle(style))
    return table


def _fmt(value, digits=2):
    """Format a number, or 'Not available' if missing."""
    number = _num(value)
    if number is None:
        return NA
    if isinstance(number, int):
        return str(number)
    return ("%." + str(digits) + "f") % number


def _fmt_mean(value):
    """Format a mean rating with 2 decimals, or 'Not available' if missing."""
    number = _num(value)
    return NA if number is None else "%.2f" % number


def _is_demo(metrics, findings):
    """True if metrics or any finding is marked synthetic."""
    if str(metrics.get("status", "")).lower() == "synthetic":
        return True
    return any(str(f.get("status", "")).lower() == "synthetic" for f in findings)


# ---------------------------------------------------------------------------
# Page decoration: top banner (demo only) + footer with page number
# ---------------------------------------------------------------------------
def _make_page_decorator(demo):
    def decorate(canvas, doc):
        canvas.saveState()
        width, height = letter
        if demo:
            canvas.setFillColor(PURPLE)
            canvas.rect(0, height - 0.45 * inch, width, 0.45 * inch, stroke=0, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawCentredString(width / 2, height - 0.3 * inch, DEMO_BANNER)
        canvas.setStrokeColor(LAVENDER)
        canvas.line(0.8 * inch, 0.65 * inch, width - 0.8 * inch, 0.65 * inch)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.8 * inch, 0.45 * inch, "Beyond Awareness | Improvement Brief")
        canvas.drawRightString(width - 0.8 * inch, 0.45 * inch, "Page %d" % doc.page)
        canvas.restoreState()
    return decorate


# ---------------------------------------------------------------------------
# Optional chart: recalled-before vs current knowledge means
# ---------------------------------------------------------------------------
def _knowledge_chart(rows, scale_max):
    """Bar chart for rows that have BOTH before and current means. Returns Drawing or None."""
    numbered = list(enumerate(rows, start=1))
    usable_pairs = [(n, r) for n, r in numbered
                    if _num(r.get("before_mean")) is not None and _num(r.get("current_mean")) is not None]
    if not usable_pairs:
        return None
    labels = ["Measure %d" % n for n, _ in usable_pairs]
    usable = [r for _, r in usable_pairs]
    before = [float(_num(r["before_mean"])) for r in usable]
    current = [float(_num(r["current_mean"])) for r in usable]
    top = _num(scale_max) or max(before + current) * 1.15
    top = max(float(top), max(before + current))

    drawing = Drawing(440, 190)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 45, 30, 380, 125
    chart.data = [before, current]
    chart.categoryAxis.categoryNames = labels
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = top
    chart.bars[0].fillColor = colors.HexColor("#B39DDB")
    chart.bars[1].fillColor = TEAL
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontSize = 8
    drawing.add(chart)
    # Simple legend
    drawing.add(Rect(60, 172, 9, 9, fillColor=colors.HexColor("#B39DDB"), strokeColor=None))
    drawing.add(String(73, 173, "Recalled before", fontSize=8))
    drawing.add(Rect(160, 172, 9, 9, fillColor=TEAL, strokeColor=None))
    drawing.add(String(173, 173, "Current", fontSize=8))
    return drawing


# ---------------------------------------------------------------------------
# Choose up to three findings for the executive summary
# ---------------------------------------------------------------------------
def _pick_summary_findings(findings):
    """Prefer findings that have numbers; skip unsupported / needs-review ones. Max 3."""
    skip = {"unsupported", "needs_review", "rejected"}
    ok = [f for f in findings if f["status"].lower() not in skip]
    with_numbers = [f for f in ok if f["count"] is not None and f["denominator"] is not None]
    without = [f for f in ok if f not in with_numbers]
    return (with_numbers + without)[:3]


def _resolve_selected(selected_interventions):
    """Accept ids or dicts with 'id' and return a clean list of ids."""
    ids = []
    for item in (selected_interventions or []):
        if isinstance(item, str):
            ids.append(item)
        elif isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


# ---------------------------------------------------------------------------
# MAIN FUNCTION: generate_report
# ---------------------------------------------------------------------------
def generate_report(metrics, findings, selected_interventions):
    """Create the PDF and return it as bytes. Never fails on empty/missing input."""
    metrics = metrics if isinstance(metrics, dict) else {}
    findings = [normalize_finding(f, i) for i, f in enumerate(findings or [])]
    plan = build_action_plan(findings, _resolve_selected(selected_interventions))
    demo = _is_demo(metrics, findings)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch, topMargin=0.9 * inch, bottomMargin=0.9 * inch,
        title="Beyond Awareness - Improvement Brief", author="Beyond Awareness team",
    )
    width = doc.width
    story = []

    # ===== COVER =====
    story.append(Spacer(1, 1.0 * inch))
    story.append(_p("Beyond Awareness", S_TITLE))
    story.append(_p("Improvement Brief for the Understanding 988 Training", S_SUB))
    if demo:
        banner = Table([[_p(DEMO_BANNER, S_BANNER)]], colWidths=[width])
        banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PURPLE),
                                    ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        story += [banner, Spacer(1, 12)]
        status_text = "DEMO - synthetic (fictional) data"
    else:
        status_text = "Real data (check that findings were validated before sharing)"

    n_resp = _num(metrics.get("n_responses"))
    if n_resp is None:
        resp_text = NA
    elif metrics.get("responses_verified"):
        resp_text = "%s (verified)" % n_resp
    else:
        resp_text = "%s (NOT verified)" % n_resp
    cover_rows = [
        ["Item", "Details"],
        ["Generated", datetime.date.today().strftime("%B %d, %Y")],
        ["Dataset period", str(metrics.get("dataset_period") or NA)],
        ["Number of responses", resp_text],
        ["Data status", status_text],
        ["Findings included", str(len(findings))],
        ["Actions selected", str(len(plan))],
    ]
    story.append(_table(cover_rows, [1.8 * inch, width - 1.8 * inch]))
    story.append(Spacer(1, 14))
    story.append(_p("This brief connects survey findings to possible training improvements and shows how "
                    "EveryMind could check whether those improvements work. It does not contain row-level "
                    "participant comments.", S_BODY))
    story.append(PageBreak())

    # ===== EXECUTIVE SUMMARY =====
    story.append(_p("1. Executive summary", S_H1))
    top = _pick_summary_findings(findings)
    if top:
        rows = [["Finding", "Source", "Numerator / denominator", "Key caveats"]]
        for f in top:
            if f["count"] is not None and f["denominator"] is not None:
                nd = "%s / %s" % (f["count"], f["denominator"])
            elif f["count"] is not None:
                nd = "%s / (denominator not available)" % f["count"]
            else:
                nd = NA
            rows.append([f["title"], f["source"], nd, "; ".join(f["limitations"]) or NA])
        story.append(_table(rows, [width * 0.33, width * 0.17, width * 0.2, width * 0.3]))
    else:
        story.append(_p("No findings were supplied, so there is nothing to summarize yet.", S_BODY))
    story.append(_p("Each finding is shown with its source, numerator and denominator. Percentages are not "
                    "causal evidence.", S_NOTE))

    # ===== TRAINING OUTCOMES =====
    story.append(_p("2. Training outcomes", S_H1))
    knowledge = [k for k in (metrics.get("knowledge") or []) if isinstance(k, dict)]
    if knowledge:
        rows = [["Knowledge measure", "Recalled-before mean", "Current mean", "Paired n"]]
        for number, k in enumerate(knowledge, start=1):
            # "Measure N" matches the chart labels below
            rows.append(["Measure %d: %s" % (number, k.get("measure") or NA), _fmt_mean(k.get("before_mean")),
                         _fmt_mean(k.get("current_mean")), _fmt(k.get("n_paired"))])
        story.append(_table(rows, [width * 0.46, width * 0.2, width * 0.18, width * 0.16]))
        story.append(Spacer(1, 6))
        chart = _knowledge_chart(knowledge, metrics.get("scale_max"))
        if chart is not None:
            story.append(chart)
    else:
        story.append(_p("Knowledge measures were not supplied (Not available).", S_BODY))
    story.append(_p(str(metrics.get("scale_note") or "Rating scale: as defined in the cleaned dataset.")
                    + " 'Before' values are recalled after the training (retrospective self-report). "
                      "Differences describe what participants reported and do not prove the training caused them.",
                    S_NOTE))

    # ===== KNOWLEDGE AND CALL INTENT =====
    story.append(_p("3. Knowledge and call intent", S_H1))
    ci = metrics.get("call_intent") if isinstance(metrics.get("call_intent"), dict) else {}
    answered, total = _num(ci.get("n_answered")), _num(ci.get("n_total"))
    if answered is not None and total:
        story.append(_p("Response coverage for 'How likely are you to call 988?': %s of %s answered (%.1f%%); "
                        "%s missing." % (answered, total, 100.0 * answered / total, total - answered), S_BODY))
    else:
        story.append(_p("Response coverage for the call-intent question: " + NA + ".", S_BODY))
    rel = metrics.get("knowledge_call_relationship")
    if isinstance(rel, dict) and rel.get("summary"):
        story.append(_p("Relationship (n = %s): %s" % (_fmt(rel.get("n")), rel["summary"]), S_BODY))
    else:
        story.append(_p("The relationship between knowledge and call intent is not available, so none is reported.", S_BODY))
    story.append(_p("Missing answers may not be random, so these results may not represent all participants.", S_NOTE))

    # ===== PARTICIPANT VOICES =====
    story.append(_p("4. Participant voices", S_H1))
    themes = [t for t in (metrics.get("themes") or []) if isinstance(t, dict)]
    validated = [t for t in themes if t.get("validated")]
    pending = len(themes) - len(validated)
    if validated:
        rows = [["Validated theme", "Count", "Out of"]]
        for t in validated:
            rows.append([str(t.get("theme") or NA), _fmt(t.get("count")), _fmt(t.get("denominator"))])
        story.append(_table(rows, [width * 0.6, width * 0.2, width * 0.2]))
    else:
        story.append(_p("No validated comment themes were supplied.", S_BODY))
    if pending > 0:
        story.append(_p("%d theme(s) are still awaiting manual validation and are not reported." % pending, S_NOTE))
    excerpts = [str(x) for x in (metrics.get("approved_excerpts") or [])]
    if excerpts:
        story.append(_p("Approved, de-identified excerpts:", S_H2))
        story += _bullets(excerpts)
    else:
        story.append(_p("No individual comments are included in this report.", S_NOTE))

    # ===== INCLUSIVE ACCESSIBILITY AUDIT =====
    story.append(_p("5. Inclusive accessibility audit", S_H1))
    story.append(_p("Each dimension is labeled Measured, Indirectly mentioned (comments only), or Unmeasured. "
                    "Nothing here assumes participants' race, gender, income, immigration status, trauma, stigma, "
                    "trust, or preferred contact method.", S_BODY))
    status_map = metrics.get("dimension_status") if isinstance(metrics.get("dimension_status"), dict) else {}
    rows = [["Dimension", "Status", "What the survey can establish", "What remains unknown"]]
    for name in DIMENSION_NAMES:
        info = DIMENSIONS[name]
        rows.append([name, str(status_map.get(name) or "Unmeasured"), info["established"], info["unknown"]])
    story.append(_table(rows, [width * 0.17, width * 0.13, width * 0.37, width * 0.33]))

    # ===== SELECTED ACTION PLAN =====
    story.append(PageBreak())
    story.append(_p("6. Selected action plan", S_H1))
    if not plan:
        story.append(_p("No actions were selected.", S_BODY))
    for number, action in enumerate(plan, start=1):
        story.append(_p("%d. %s" % (number, action["title"]), S_H2))
        steps = [_p("%d. %s" % (i, s), S_SMALL) for i, s in enumerate(action["steps"], start=1)]
        rows = [
            ["Item", "Details"],
            ["Current evidence", action["current_evidence"]],
            ["Why suggested", action["why"]],
            ["Proposed change", action["proposed_change"]],
            ["Concrete steps", steps],
            ["Suggested owner", action["owner"]],
            ["Effort", "%s (%s)" % (action["effort"], action["effort_note"])],
            ["Success metric", action["future_measurement"]],
            ["Follow-up timing", action["checkin"]],
            ["What would change our mind", action["decision_rule"]],
            ["Limitations", [_p("- " + c, S_SMALL) for c in action["caveats"]] or "None listed"],
        ]
        story.append(_table(rows, [1.5 * inch, width - 1.5 * inch]))
        story.append(Spacer(1, 6))

    # ===== EVALUATION ROADMAP =====
    story.append(_p("7. Evaluation roadmap", S_H1))
    story.append(_p("What to collect at the next session:", S_H2))
    next_items = ["Keep the same three knowledge items and the call-intent question so results can be compared.",
                  "Record how many people answered each question (response coverage).",
                  "Add any optional questions listed below for the chosen actions."]
    story += _bullets(next_items)
    story.append(_p("Optional later follow-up:", S_H2))
    story.append(_p("An optional follow-up (timing chosen by EveryMind) could show what participants remember "
                    "and whether people who respond differ from people who do not.", S_BODY))
    story.append(_p("Decision rules for the selected actions:", S_H2))
    if plan:
        rows = [["Action", "What to measure", "When", "Decision rule"]]
        for action in plan:
            rows.append([action["title"], action["future_measurement"], action["checkin"], action["decision_rule"]])
        story.append(_table(rows, [width * 0.18, width * 0.28, width * 0.17, width * 0.37]))
        touched = []
        for action in plan:
            for dim in action["dimensions"]:
                if dim not in touched:
                    touched.append(dim)
        if touched:
            story.append(_p("Optional future survey questions (for the dimensions these actions touch):", S_H2))
            for dim in touched:
                for q in DIMENSIONS[dim]["future_questions"]:
                    story.append(_p("- [%s] %s" % (dim, q), S_SMALL))
    else:
        story.append(_p("Select actions in the Action Lab to see decision rules here.", S_BODY))

    # ===== METHODS AND LIMITATIONS =====
    story.append(_p("8. Methods and limitations", S_H1))
    limits = [
        "Retrospective self-report: 'before' ratings are recalled after training and may be biased.",
        "Missing data: some questions (especially call intent) have incomplete answers.",
        "Sample sizes: small groups can give unstable results and should not be over-interpreted.",
        "Observational interpretation: patterns are not proof that the training caused them.",
        "Effort levels are planning estimates, not proven impact or success probabilities.",
        "The survey does not measure cultural, socioeconomic, communication, trust, or psychological barriers directly.",
        "Comment themes count only if manually validated.",
    ]
    story += _bullets(limits)

    decorate = _make_page_decorator(demo)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()