import io
import subprocess
import sys

from intervention_planner import (FINDING_TYPE_MAP, INTERVENTIONS, build_action_plan, evidence_text,
                                  list_interventions, recommend_interventions)
from report_generator import generate_report
from sample_findings import get_synthetic_findings, get_synthetic_metrics


def _finding(type_, **extra):
    """Small helper: make a minimal finding of a given type."""
    base = {"id": "t_" + str(type_), "source": "test", "type": type_, "title": "Test " + str(type_),
            "description": "", "count": 5, "denominator": 10, "percentage": 50.0,
            "limitations": ["test"], "evidence": {}, "status": "synthetic"}
    base.update(extra)
    return base


# ---------------- catalog ----------------
def test_catalog_has_12_catalog_options_with_steps_and_metrics():
    catalog = [i for i in list_interventions() if i["kind"] == "catalog"]
    assert len(catalog) == 12
    for item in list_interventions():
        assert item["steps"], item["id"] + " needs steps"
        assert item["metric"], item["id"] + " needs a metric"
        assert item["effort"] in ("Low", "Medium", "High")
        assert item["change_mind"], item["id"] + " needs a 'what would change our mind'"


# ---------------- matching ----------------
def test_first_recommendation_matches_the_brief():
    expected_first = {
        "knowledge_action_gap": "help_seeking_confidence",
        "low_when_knowledge": "crisis_scenarios",
        "communication_measurement_gap": "contact_method",
        "privacy_measurement_gap": "accessibility_question_pack",
        "privacy_feedback_concern": "confidentiality_explained",
        "requests_more_examples": "crisis_scenarios",
        "low_presenter_engagement": "presenter_improvement_loop",
        "small_group_sample": "collect_more_evidence",
        "low_call_intent_response_rate": "survey_design_fix",
    }
    for type_, first_id in expected_first.items():
        result = recommend_interventions([_finding(type_)])
        ids = result["by_finding"]["t_" + type_]["intervention_ids"]
        assert ids[0] == first_id, type_
        assert 1 <= len(ids) <= 3


def test_every_mapped_id_exists_and_max_three():
    for type_, ids in FINDING_TYPE_MAP.items():
        assert 1 <= len(ids) <= 3
        for i in ids:
            assert i in INTERVENTIONS


def test_two_unrelated_findings_give_different_actions():
    a = recommend_interventions([_finding("knowledge_action_gap")])["recommendations"][0]["id"]
    b = recommend_interventions([_finding("low_presenter_engagement")])["recommendations"][0]["id"]
    assert a != b


def test_deduplication_and_traceability():
    findings = [_finding("requests_more_examples", id="a"), _finding("low_when_knowledge", id="b")]
    recs = recommend_interventions(findings)["recommendations"]
    ids = [r["id"] for r in recs]
    assert len(ids) == len(set(ids))                       # no duplicates
    scenarios = [r for r in recs if r["id"] == "crisis_scenarios"][0]
    assert {t["id"] for t in scenarios["triggered_by"]} == {"a", "b"}   # both findings remembered


def test_privacy_measurement_gap_only_investigates():
    recs = recommend_interventions([_finding("privacy_measurement_gap")])["recommendations"]
    conf = [r for r in recs if r["id"] == "confidentiality_explained"][0]
    assert "investigate" in conf["triggered_by"][0]["note"].lower()


# ---------------- empty / partial / unknown ----------------
def test_zero_findings():
    assert recommend_interventions([])["recommendations"] == []
    assert recommend_interventions(None)["recommendations"] == []
    assert build_action_plan([], []) == []
    assert build_action_plan(None, None) == []


def test_unknown_or_missing_type_is_needs_review():
    result = recommend_interventions([{"id": "x", "type": "made_up"}, {"id": "y"}, "not a dict", None])
    assert result["recommendations"] == []
    assert len(result["needs_review"]) == 4
    for entry in result["by_finding"].values():
        assert entry["status"] == "needs_review"


def test_unknown_selected_ids_are_ignored():
    plan = build_action_plan(get_synthetic_findings(), ["does_not_exist", "myth_vs_reality", "myth_vs_reality"])
    assert [p["id"] for p in plan] == ["myth_vs_reality"]      # unknown skipped, duplicate removed


# ---------------- no invented evidence ----------------
def test_missing_numbers_stay_missing():
    text = evidence_text({"id": "m", "type": "knowledge_action_gap", "title": "No numbers", "count": None,
                          "denominator": None, "percentage": None, "status": "validated"})
    assert "not available" in text
    assert "None" not in text and "0.0%" not in text and "0 of" not in text


def test_zero_denominator_does_not_crash():
    text = evidence_text({"title": "Zero", "count": 3, "denominator": 0})
    assert "%" not in text


def test_plan_without_trigger_does_not_invent_evidence():
    plan = build_action_plan([], ["myth_vs_reality"])
    assert "No current finding triggers" in plan[0]["current_evidence"]


# ---------------- PDF ----------------
def _is_pdf(data):
    return isinstance(data, bytes) and data.startswith(b"%PDF") and b"%%EOF" in data[-1024:]


def test_pdf_full_demo():
    data = generate_report(get_synthetic_metrics(), get_synthetic_findings(),
                           ["help_seeking_confidence", "myth_vs_reality", "contact_method"])
    assert _is_pdf(data)
    try:
        from pypdf import PdfReader
    except ImportError:
        return
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) >= 4
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "SYNTHETIC DEMONSTRATION - NOT EVERYMIND RESULTS" in text
    assert "Selected action plan" in text


def test_pdf_empty_inputs():
    assert _is_pdf(generate_report({}, [], []))
    assert _is_pdf(generate_report(None, None, None))


def test_pdf_partial_and_odd_text():
    findings = [{"id": "p", "type": "knowledge_action_gap", "title": "A & B <tag> test"}]
    metrics = {"knowledge": [{"measure": "Only before <1>", "before_mean": 3.0}], "themes": [{"theme": "x"}]}
    assert _is_pdf(generate_report(metrics, findings, [{"id": "myth_vs_reality"}, "bad_id"]))


def test_real_data_has_no_demo_banner():
    data = generate_report({"status": "validated"}, [_finding("knowledge_action_gap", status="validated")],
                           ["myth_vs_reality"])
    assert _is_pdf(data)
    try:
        from pypdf import PdfReader
    except ImportError:
        return
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)
    assert "SYNTHETIC DEMONSTRATION" not in text


# ---------------- real data adapter (uses a tiny FAKE spreadsheet, never the real CSV) ----------------
def _mini_survey():
    """A 6-row fake survey that copies the real column layout, including messy values."""
    import pandas as pd
    cur = "Please tell us how much you disagree or agree with the statements..I %s."
    bef = "Now think back to before you took part in the Understanding 988 training.\xa0\xa0.I %s."
    rows = {
        "Id": [1, 2, 3, 4, 5, 6],
        "Start time": ["2025-10-21 10:00:00"] * 3 + ["2026-05-02 10:00:00"] * 3,
        "Language": ["English (United States)\u200e"] * 5 + ["Espa\u00f1ol (M\u00e9xico)\u200e"],
        "Are you a....?": ["Student", "School staff member;", "Student", "Caregiver/parent;Student", "Student", "Student"],
        "Please enter the date of your training.": ["2025-10-21"] * 5 + [None],
        "Which county is this training affiliated with?\xa0": ["Montgomery County with NAMI MC", "Anne Arundel",
                                                             "Anne Arundel ", "Fairfax county", "Anne Arundel", "Harris"],
        cur % "can identify mental health challenges and crises": ["Strongly agree ", "Agree", "Agree", "Disagree", "Agree", "Agree"],
        cur % "can describe 988 and how it works": ["Agree"] * 6,
        cur % "know when to use 988": ["Agree"] * 6,
        bef % "could identify mental health challenges and crises": ["Agree", "Disagree", "Agree", "Disagree", "Agree", None],
        bef % "could describe 988 and how it works": ["Disagree"] * 6,
        bef % "knew when to use 988": ["Disagree"] * 6,
        "How likely are you to call 988 if you or someone else is experiencing a mental health challenge or crisis?":
            [None, None, None, 7, 3, None],
        "What was the most valuable thing you learned during the training?\xa0": ["SECRET COMMENT ONE"] * 6,
        "How can we improve this training in the future?": ["SECRET COMMENT TWO"] * 6,
    }
    return pd.DataFrame(rows)


def test_adapter_numbers_are_correct():
    from real_data_adapter import build_real_inputs
    findings, metrics, summary = build_real_inputs(_mini_survey())
    assert metrics["n_responses"] == 6 and metrics["responses_verified"] is True
    assert metrics["call_intent"] == {"n_answered": 2, "n_total": 6}
    first = metrics["knowledge"][0]                       # paired rows = 5 (row 6 has no 'before')
    assert first["n_paired"] == 5
    assert first["current_mean"] == 3.8 and first["before_mean"] == 3.2   # (5+4+4+2+4)/5 and (4+2+4+2+4)/5
    assert summary["counties"]["Montgomery"] == 1 and summary["counties"]["Anne Arundel"] == 3
    assert summary["counties"]["Fairfax"] == 1 and summary["counties"]["Other / unclear"] == 1
    assert summary["languages"]["Espa\u00f1ol (M\u00e9xico)"] == 1     # hidden characters removed
    # months with fewer than 5 rows are NOT flagged as "no answers" (too few rows to say anything)
    assert "no answers at all" not in " ".join(findings[0]["limitations"])


def test_adapter_findings_are_valid_and_safe():
    import json
    from real_data_adapter import build_real_inputs
    findings, metrics, summary = build_real_inputs(_mini_survey())
    for f in findings:
        assert f["type"] in FINDING_TYPE_MAP, f["type"]            # every type is recognized by the planner
        assert f["status"] != "synthetic"
    json.dumps(findings), json.dumps(metrics)                      # plain python types only
    everything = json.dumps([findings, metrics, summary])
    assert "SECRET COMMENT" not in everything                      # no open-ended comments leak out
    result = recommend_interventions(findings)
    assert result["recommendations"] and not result["needs_review"]


def test_adapter_missing_columns_do_not_crash():
    import pandas as pd
    from real_data_adapter import build_real_inputs
    findings, metrics, summary = build_real_inputs(pd.DataFrame({"Id": [1, 2], "Something else": ["a", "b"]}))
    assert metrics["n_responses"] == 2 and metrics["knowledge"] == []
    assert metrics["call_intent"]["n_answered"] is None            # missing stays missing, not 0
    assert _is_pdf(generate_report(metrics, findings, ["myth_vs_reality"]))


def test_adapter_empty_file_gives_clear_error():
    import pandas as pd
    from real_data_adapter import build_real_inputs
    try:
        build_real_inputs(pd.DataFrame())
    except ValueError as error:
        assert "no rows" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_pdf_with_real_style_inputs_has_no_demo_banner():
    from real_data_adapter import build_real_inputs
    findings, metrics, _ = build_real_inputs(_mini_survey())
    data = generate_report(metrics, findings, ["survey_design_fix", "collect_more_evidence"])
    assert _is_pdf(data)
    try:
        from pypdf import PdfReader
    except ImportError:
        return
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)
    assert "SYNTHETIC DEMONSTRATION" not in text and "Real data" in text


# ---------------- no streamlit in the logic modules ----------------
def test_logic_modules_do_not_import_streamlit():
    code = ("import sys, intervention_planner, report_generator, sample_findings; "
            "print('streamlit' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stderr


# ---------------- run without pytest ----------------
if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, func in tests:
        try:
            func()
            print("PASS", name)
        except Exception as error:
            failed += 1
            print("FAIL", name, "->", repr(error))
    print("\n%d tests, %d failed" % (len(tests), failed))
    sys.exit(1 if failed else 0)