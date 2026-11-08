"""Synthetic tests; no real workbook, participant data, or network required.

Run: python -m pytest test_data_pipeline.py -q
UI tests run when streamlit and plotly are installed; otherwise they skip.
The future team's analytical findings/PDF implementations are not tested here.
"""

from io import BytesIO
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

import cleaning as c
import pipeline as p


def row(**updates):
    record = dict.fromkeys(c.EXPECTED_COLUMNS, "")
    record.update(id="synthetic-id", county="Fairfax", language="English",
                  participant_type="Student", training_date="2026-01-05")
    record.update({col: "Agree" for col in c.KNOWLEDGE_COLUMNS})
    record.update(updates)
    return record


def clean(*records):
    return c.clean_survey(pd.DataFrame(records, columns=c.EXPECTED_COLUMNS))


def workbook_bytes(frame, sheet="Survey Data"):
    output = BytesIO()
    frame.to_excel(output, index=False, sheet_name=sheet, engine="openpyxl")
    output.seek(0)
    return output


def test_load_original_headers_and_preserve_raw():
    source = pd.DataFrame([list(row().values())], columns=c.SOURCE_HEADERS)
    # Workbook uses nonbreaking spaces and a trailing space in some headers.
    source = source.rename(columns={source.columns[6]: source.columns[6] + "\u00a0"})
    loaded = c.load_survey(workbook_bytes(source))
    before = loaded.copy(deep=True)
    cleaned, audit = c.clean_survey(loaded)
    assert_frame_equal(loaded, before)
    assert loaded.shape == (1, 20)
    assert cleaned["after_identify"].iloc[0] == 4
    assert cleaned["after_identify_raw"].iloc[0] == "Agree"
    assert audit["original_row_count"] == 1


def test_schema_accepts_reordered_contract():
    source = pd.DataFrame([row()])[list(reversed(c.EXPECTED_COLUMNS))]
    assert c.validate_schema(source)["valid"]
    cleaned, _ = c.clean_survey(source)
    assert cleaned["county"].iloc[0] == "Fairfax"


@pytest.mark.parametrize("problem", ["missing", "extra", "duplicate", "wrong_question"])
def test_bad_schema_fails_clearly(problem):
    source = pd.DataFrame([row()])
    if problem == "missing":
        source = source.drop(columns="id")
    elif problem == "extra":
        source["unexpected"] = ""
    elif problem == "duplicate":
        source.columns = ["county" if col == "id" else col for col in source.columns]
    else:
        source = source.rename(columns={"county": "Different survey question"})
    assert not c.validate_schema(source)["valid"]
    with pytest.raises(ValueError, match="schema mismatch"):
        c.clean_survey(source)


def test_wrong_sheet_fails():
    with pytest.raises(ValueError):
        c.load_survey(workbook_bytes(pd.DataFrame([row()]), sheet="Wrong sheet"))


@pytest.mark.parametrize("value,expected", [
    ("Montgomery County with NAMI MC", "Montgomery"),
    (" Fairfax county ", "Fairfax"), ("Prince George’s County", "Prince George's"),
    ("Queen Anne's County ", "Queen Anne's"), ("Harris county", "Harris"),
])
def test_county_normalization(value, expected):
    assert c.normalize_county(value) == expected


def test_unknown_and_missing_counties_are_not_guessed():
    d, audit = clean(row(county="Unlisted training location"), row(county=""))
    assert d["county"].iloc[0] == "Unlisted training location"
    assert pd.isna(d["county"].iloc[1])
    assert audit["unmapped_categories"]["county"] == 1


def test_roles_deduplicate_within_rows_but_overlap_across_groups():
    d, _ = clean(row(participant_type="Student;Caregiver/parent;Student;"), row(id="two"))
    assert d["role_list"].iloc[0] == ["Student", "Caregiver/parent"]
    assert d["role_raw"].iloc[0] == "Student;Caregiver/parent;Student;"
    overview = p.build_summary(d)["overview"]
    assert overview["survey_rows"] == 2
    assert overview["total_role_selections"] == 3
    assert len(p.filter_survey(d, roles=["Student", "Caregiver/parent"])) == 2


def test_missing_and_unknown_roles():
    d, audit = clean(row(participant_type=""), row(participant_type="Unknown role"))
    assert d["role_list"].iloc[0] == []
    assert pd.isna(d["participant_type"].iloc[0])
    assert d["role_list"].iloc[1] == ["Other/unclassified"]
    assert audit["unmapped_categories"]["role_rows"] == 1


@pytest.mark.parametrize("value,score", [
    ("Strongly disagree", 1), ("disagree", 2),
    (" Neither agree nor disagree ", 3), ("AGREE", 4), ("Strongly agree\u00a0", 5),
])
def test_standard_likert_values(value, score):
    d, _ = clean(row(after_identify=value))
    assert d["after_identify"].iloc[0] == score


def test_nonstandard_presenter_answers_are_flagged():
    d, audit = clean(row(presenter_engagement="Neither agree or disagree",
                         presenter_expertise="Satisfied", training_organization="Very agree"))
    assert d["presenter_engagement"].iloc[0] == 3
    for field in ["presenter_expertise", "training_organization"]:
        assert pd.isna(d[field].iloc[0])
        assert d[f"{field}_invalid"].iloc[0]
        assert audit["invalid_values"][field] == 1
    assert d["presenter_expertise_raw"].iloc[0] == "Satisfied"


@pytest.mark.parametrize("field", ["recommend_training", "willingness_to_call"])
@pytest.mark.parametrize("value,expected,invalid", [
    ("", None, False), (None, None, False), (0, 0, False),
    ("10", 10, False), (5.5, 5.5, False), (11, None, True),
    (-1, None, True), ("bad", None, True), (float("inf"), None, True),
])
def test_zero_to_ten_and_missingness(field, value, expected, invalid):
    d, _ = clean(row(**{field: value}))
    if expected is None:
        assert pd.isna(d[field].iloc[0])
    else:
        assert d[field].iloc[0] == expected
    assert bool(d[f"{field}_invalid"].iloc[0]) is invalid


def test_dates_duplicate_ids_and_blank_ids_are_audited():
    d, audit = clean(row(id="repeat", training_date="bad date"),
                     row(id="repeat", training_date="2026-01-05"), row(id="", training_date=""))
    assert audit["date_failures"]["training_date"] == 1
    assert d["training_date_raw"].iloc[0] == "bad date"
    assert audit["duplicate_ids"] == {
        "rows_with_duplicate_id": 2, "distinct_duplicate_ids": 1,
        "extra_rows_beyond_first": 1, "missing_id_rows": 1,
    }
    assert len(d) == 3  # No silent deduplication.


def test_paired_metrics_exclude_unmatched_rows():
    d, _ = clean(row(before_identify="Disagree", after_identify="Agree"),
                 row(before_identify="Strongly agree", after_identify=""),
                 row(before_identify="", after_identify="Strongly disagree"))
    stats = p.summarize_knowledge(d)["topics"]["Identify crisis"]
    assert stats["n"] == 1
    assert stats["denominator_rows"] == 3
    assert stats["missing_pair_rows"] == 2
    assert stats["before_mean"] == 2
    assert stats["after_mean"] == 4
    assert stats["mean_change"] == 2
    assert stats["share_up"] == 1
    distributions = p.summarize_distributions(d)["knowledge_paired"]["Identify crisis"]
    assert distributions["before"]["valid_n"] == distributions["after"]["valid_n"] == 1


def test_changes_count_increases_ties_and_decreases():
    d, _ = clean(row(before_when="Disagree", after_when="Agree"),
                 row(before_when="Agree", after_when="Agree"),
                 row(before_when="Strongly agree", after_when="Disagree"))
    stats = p.summarize_knowledge(d)["topics"]["Know when to use 988"]
    assert (stats["count_up"], stats["count_same"], stats["count_down"]) == (1, 1, 1)
    assert stats["share_up"] == pytest.approx(1 / 3)
    assert stats["mean_change"] == pytest.approx(-1 / 3)


def test_overall_requires_all_six_answers():
    d, _ = clean(row(after_identify="Strongly agree"), row(before_describe=""))
    stats = p.summarize_knowledge(d)["overall_three_topic_mean"]
    assert stats["n"] == 1
    assert stats["missing_pair_rows"] == 1
    assert stats["mean_change"] == pytest.approx(1 / 3)


def test_missingness_separates_blank_invalid_and_valid_zero():
    d, _ = clean(row(willingness_to_call=""), row(willingness_to_call=11), row(willingness_to_call=0))
    missing = next(v for v in p.summarize_missingness(d) if v["field"] == "willingness_to_call")
    assert missing["source_missing_n"] == 1
    assert missing["invalid_or_unusable_n"] == 1
    assert missing["usable_n"] == 1
    assert p.build_summary(d)["overview"]["willingness_response_rate"] == pytest.approx(1 / 3)


def test_group_suppression_uses_paired_n_and_threshold_boundary():
    d, _ = clean(row(), row(before_identify=""))
    groups = p.summarize_group_comparisons(d, min_group_n=2)["county"]
    stats = groups[0]["knowledge"]["topics"]
    assert stats["Identify crisis"]["suppressed"]
    assert stats["Identify crisis"]["mean_change"] is None
    assert stats["Identify crisis"]["share_up"] is None
    assert not stats["Describe 988"]["suppressed"]
    assert stats["Describe 988"]["mean_change"] == 0


def test_filters_intersect_and_keep_end_date():
    d, _ = clean(row(training_date="2026-01-05"), row(county="Montgomery"),
                 row(language="Spanish"), row(training_date="2026-01-06"))
    filtered = p.filter_survey(d, counties=["Fairfax"], languages=["English"],
                               roles=["Student"], start_date="2026-01-05", end_date="2026-01-05")
    assert len(filtered) == 1
    assert len(p.filter_survey(d)) == 4


def test_empty_selection_has_safe_undefined_metrics():
    d, _ = clean(row())
    empty = p.filter_survey(d, counties=["No matching county"])
    summary = p.build_summary(empty)
    assert summary["overview"]["survey_rows"] == 0
    assert summary["overview"]["willingness_response_rate"] is None
    assert summary["knowledge"]["topics"]["Identify crisis"]["mean_change"] is None
    json.dumps(summary, allow_nan=False)


def test_export_contains_aggregates_not_comments_or_identifiers(tmp_path):
    d, _ = clean(row(id="PRIVATE-ID-MARKER", valuable_feedback="PRIVATE-COMMENT-MARKER"))
    path = p.export_summary(d, tmp_path / "summary.json")
    text = path.read_text(encoding="utf-8")
    exported = json.loads(text)
    assert exported["overview"]["survey_rows"] == 1
    assert "PRIVATE-ID-MARKER" not in text
    assert "PRIVATE-COMMENT-MARKER" not in text
    assert "valuable_feedback_raw" not in text


def test_pipeline_in_memory_end_to_end():
    result = p.run_pipeline(workbook_bytes(pd.DataFrame([row()])))
    assert result.raw_df.shape == (1, 20)
    assert result.summary["overview"]["survey_rows"] == 1
    assert result.quality["original_row_count"] == 1


@pytest.fixture
def app_module():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    import app
    return app


def test_optional_module_absent_vs_broken(app_module, monkeypatch):
    def absent(_):
        raise ModuleNotFoundError("missing", name="gap_detector")
    monkeypatch.setattr(app_module.importlib, "import_module", absent)
    assert app_module.load_optional_module("Gap Detector")[1] == "missing"
    def broken(_):
        raise ModuleNotFoundError("missing dependency", name="missing_dependency")
    monkeypatch.setattr(app_module.importlib, "import_module", broken)
    assert app_module.load_optional_module("Gap Detector")[1] == "broken"


def test_missing_function_is_contract_error(app_module, monkeypatch):
    monkeypatch.setattr(app_module.importlib, "import_module", lambda _: SimpleNamespace())
    assert app_module.load_optional_module("Gap Detector")[1] == "contract_error"


def test_finding_schema_and_private_evidence(app_module):
    finding = dict(id="synthetic", source="test", type="test", title="Demo finding",
                   description="An aggregate finding.", count=1, denominator=2,
                   percentage=50, limitations=["Synthetic"], evidence={"private": "Do not forward"})
    assert app_module.validate_findings({"findings": [finding]})[0]["evidence"] == {}
    finding["percentage"] = 150
    with pytest.raises(ValueError):
        app_module.validate_findings({"findings": [finding]})


def test_app_starts_and_all_navigation_survives_missing_team_modules(app_module, monkeypatch):
    from streamlit.testing.v1 import AppTest
    for module, _ in app_module.MODULES.values():
        monkeypatch.setitem(sys.modules, module, None)
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    assert not at.exception
    assert at.metric[0].value == "180"
    assert any("SYNTHETIC" in warning.value for warning in at.warning)
    for page in app_module.PAGES[1:]:
        at.sidebar.radio(key="workspace_page").set_value(page).run()
        assert not at.exception
        assert any("progress" in message.value for message in at.info)


def test_app_filters_change_the_same_dashboard_counts(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.multiselect(key="filter_counties").set_value(["Fairfax"]).run()
    assert not at.exception
    assert at.metric[0].value == "45"
    at.sidebar.multiselect(key="filter_roles").set_value(["Student"]).run()
    assert not at.exception
    assert any("No survey rows match" in message.value for message in at.info)


def test_app_upload_mode_has_safe_empty_state(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.radio(key="source_mode").set_value("Upload survey workbook").run()
    assert not at.exception
    assert any("Choose your survey" in message.value for message in at.info)


def test_app_upload_replacement_and_bad_schema_clear_old_results(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.radio(key="source_mode").set_value("Upload survey workbook").run()
    if not hasattr(at, "file_uploader") or not hasattr(at.file_uploader[0], "set_value"):
        pytest.skip("This Streamlit version does not simulate file uploads.")
    content = workbook_bytes(pd.DataFrame([row(), row(id="second")])).getvalue()
    at.file_uploader[0].set_value(("synthetic.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.metric[0].value == "2"
    # Replacement workbooks must produce new counts, not stale cached results.
    replacement = workbook_bytes(pd.DataFrame([row(county="Montgomery")])).getvalue()
    at.file_uploader[0].set_value(("replacement.xlsx", replacement, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.metric[0].value == "1"
    bad = workbook_bytes(pd.DataFrame({"wrong": ["test"]})).getvalue()
    at.file_uploader[0].set_value(("bad.xlsx", bad, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.error
    assert not at.metric
    assert "uploaded_result" not in at.session_state


def test_app_date_and_group_controls(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.checkbox(key="filter_dates_enabled").check().run()
    assert not at.exception
    assert at.metric[0].value == "175"  # Five synthetic rows have invalid dates.
    for field in ["role", "language"]:
        at.selectbox(key="comparison_group").set_value(field).run()
        at.selectbox(key="coverage_group").set_value(field).run()
        assert not at.exception
"""Synthetic tests; no real workbook, participant data, or network required.

Run: python -m pytest test_data_pipeline.py -q
UI tests run when streamlit and plotly are installed; otherwise they skip.
The future team's analytical findings/PDF implementations are not tested here.
"""

from io import BytesIO
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

import cleaning as c
import pipeline as p


def row(**updates):
    record = dict.fromkeys(c.EXPECTED_COLUMNS, "")
    record.update(id="synthetic-id", county="Fairfax", language="English",
                  participant_type="Student", training_date="2026-01-05")
    record.update({col: "Agree" for col in c.KNOWLEDGE_COLUMNS})
    record.update(updates)
    return record


def clean(*records):
    return c.clean_survey(pd.DataFrame(records, columns=c.EXPECTED_COLUMNS))


def workbook_bytes(frame, sheet="Survey Data"):
    output = BytesIO()
    frame.to_excel(output, index=False, sheet_name=sheet, engine="openpyxl")
    output.seek(0)
    return output


def test_load_original_headers_and_preserve_raw():
    source = pd.DataFrame([list(row().values())], columns=c.SOURCE_HEADERS)
    # Workbook uses nonbreaking spaces and a trailing space in some headers.
    source = source.rename(columns={source.columns[6]: source.columns[6] + "\u00a0"})
    loaded = c.load_survey(workbook_bytes(source))
    before = loaded.copy(deep=True)
    cleaned, audit = c.clean_survey(loaded)
    assert_frame_equal(loaded, before)
    assert loaded.shape == (1, 20)
    assert cleaned["after_identify"].iloc[0] == 4
    assert cleaned["after_identify_raw"].iloc[0] == "Agree"
    assert audit["original_row_count"] == 1


def test_schema_accepts_reordered_contract():
    source = pd.DataFrame([row()])[list(reversed(c.EXPECTED_COLUMNS))]
    assert c.validate_schema(source)["valid"]
    cleaned, _ = c.clean_survey(source)
    assert cleaned["county"].iloc[0] == "Fairfax"


@pytest.mark.parametrize("problem", ["missing", "extra", "duplicate", "wrong_question"])
def test_bad_schema_fails_clearly(problem):
    source = pd.DataFrame([row()])
    if problem == "missing":
        source = source.drop(columns="id")
    elif problem == "extra":
        source["unexpected"] = ""
    elif problem == "duplicate":
        source.columns = ["county" if col == "id" else col for col in source.columns]
    else:
        source = source.rename(columns={"county": "Different survey question"})
    assert not c.validate_schema(source)["valid"]
    with pytest.raises(ValueError, match="schema mismatch"):
        c.clean_survey(source)


def test_wrong_sheet_fails():
    with pytest.raises(ValueError):
        c.load_survey(workbook_bytes(pd.DataFrame([row()]), sheet="Wrong sheet"))


@pytest.mark.parametrize("value,expected", [
    ("Montgomery County with NAMI MC", "Montgomery"),
    (" Fairfax county ", "Fairfax"), ("Prince George’s County", "Prince George's"),
    ("Queen Anne's County ", "Queen Anne's"), ("Harris county", "Harris"),
])
def test_county_normalization(value, expected):
    assert c.normalize_county(value) == expected


def test_unknown_and_missing_counties_are_not_guessed():
    d, audit = clean(row(county="Unlisted training location"), row(county=""))
    assert d["county"].iloc[0] == "Unlisted training location"
    assert pd.isna(d["county"].iloc[1])
    assert audit["unmapped_categories"]["county"] == 1


def test_roles_deduplicate_within_rows_but_overlap_across_groups():
    d, _ = clean(row(participant_type="Student;Caregiver/parent;Student;"), row(id="two"))
    assert d["role_list"].iloc[0] == ["Student", "Caregiver/parent"]
    assert d["role_raw"].iloc[0] == "Student;Caregiver/parent;Student;"
    overview = p.build_summary(d)["overview"]
    assert overview["survey_rows"] == 2
    assert overview["total_role_selections"] == 3
    assert len(p.filter_survey(d, roles=["Student", "Caregiver/parent"])) == 2


def test_missing_and_unknown_roles():
    d, audit = clean(row(participant_type=""), row(participant_type="Unknown role"))
    assert d["role_list"].iloc[0] == []
    assert pd.isna(d["participant_type"].iloc[0])
    assert d["role_list"].iloc[1] == ["Other/unclassified"]
    assert audit["unmapped_categories"]["role_rows"] == 1


@pytest.mark.parametrize("value,score", [
    ("Strongly disagree", 1), ("disagree", 2),
    (" Neither agree nor disagree ", 3), ("AGREE", 4), ("Strongly agree\u00a0", 5),
])
def test_standard_likert_values(value, score):
    d, _ = clean(row(after_identify=value))
    assert d["after_identify"].iloc[0] == score


def test_nonstandard_presenter_answers_are_flagged():
    d, audit = clean(row(presenter_engagement="Neither agree or disagree",
                         presenter_expertise="Satisfied", training_organization="Very agree"))
    assert d["presenter_engagement"].iloc[0] == 3
    for field in ["presenter_expertise", "training_organization"]:
        assert pd.isna(d[field].iloc[0])
        assert d[f"{field}_invalid"].iloc[0]
        assert audit["invalid_values"][field] == 1
    assert d["presenter_expertise_raw"].iloc[0] == "Satisfied"


@pytest.mark.parametrize("field", ["recommend_training", "willingness_to_call"])
@pytest.mark.parametrize("value,expected,invalid", [
    ("", None, False), (None, None, False), (0, 0, False),
    ("10", 10, False), (5.5, 5.5, False), (11, None, True),
    (-1, None, True), ("bad", None, True), (float("inf"), None, True),
])
def test_zero_to_ten_and_missingness(field, value, expected, invalid):
    d, _ = clean(row(**{field: value}))
    if expected is None:
        assert pd.isna(d[field].iloc[0])
    else:
        assert d[field].iloc[0] == expected
    assert bool(d[f"{field}_invalid"].iloc[0]) is invalid


def test_dates_duplicate_ids_and_blank_ids_are_audited():
    d, audit = clean(row(id="repeat", training_date="bad date"),
                     row(id="repeat", training_date="2026-01-05"), row(id="", training_date=""))
    assert audit["date_failures"]["training_date"] == 1
    assert d["training_date_raw"].iloc[0] == "bad date"
    assert audit["duplicate_ids"] == {
        "rows_with_duplicate_id": 2, "distinct_duplicate_ids": 1,
        "extra_rows_beyond_first": 1, "missing_id_rows": 1,
    }
    assert len(d) == 3  # No silent deduplication.


def test_paired_metrics_exclude_unmatched_rows():
    d, _ = clean(row(before_identify="Disagree", after_identify="Agree"),
                 row(before_identify="Strongly agree", after_identify=""),
                 row(before_identify="", after_identify="Strongly disagree"))
    stats = p.summarize_knowledge(d)["topics"]["Identify crisis"]
    assert stats["n"] == 1
    assert stats["denominator_rows"] == 3
    assert stats["missing_pair_rows"] == 2
    assert stats["before_mean"] == 2
    assert stats["after_mean"] == 4
    assert stats["mean_change"] == 2
    assert stats["share_up"] == 1
    distributions = p.summarize_distributions(d)["knowledge_paired"]["Identify crisis"]
    assert distributions["before"]["valid_n"] == distributions["after"]["valid_n"] == 1


def test_changes_count_increases_ties_and_decreases():
    d, _ = clean(row(before_when="Disagree", after_when="Agree"),
                 row(before_when="Agree", after_when="Agree"),
                 row(before_when="Strongly agree", after_when="Disagree"))
    stats = p.summarize_knowledge(d)["topics"]["Know when to use 988"]
    assert (stats["count_up"], stats["count_same"], stats["count_down"]) == (1, 1, 1)
    assert stats["share_up"] == pytest.approx(1 / 3)
    assert stats["mean_change"] == pytest.approx(-1 / 3)


def test_overall_requires_all_six_answers():
    d, _ = clean(row(after_identify="Strongly agree"), row(before_describe=""))
    stats = p.summarize_knowledge(d)["overall_three_topic_mean"]
    assert stats["n"] == 1
    assert stats["missing_pair_rows"] == 1
    assert stats["mean_change"] == pytest.approx(1 / 3)


def test_missingness_separates_blank_invalid_and_valid_zero():
    d, _ = clean(row(willingness_to_call=""), row(willingness_to_call=11), row(willingness_to_call=0))
    missing = next(v for v in p.summarize_missingness(d) if v["field"] == "willingness_to_call")
    assert missing["source_missing_n"] == 1
    assert missing["invalid_or_unusable_n"] == 1
    assert missing["usable_n"] == 1
    assert p.build_summary(d)["overview"]["willingness_response_rate"] == pytest.approx(1 / 3)


def test_group_suppression_uses_paired_n_and_threshold_boundary():
    d, _ = clean(row(), row(before_identify=""))
    groups = p.summarize_group_comparisons(d, min_group_n=2)["county"]
    stats = groups[0]["knowledge"]["topics"]
    assert stats["Identify crisis"]["suppressed"]
    assert stats["Identify crisis"]["mean_change"] is None
    assert stats["Identify crisis"]["share_up"] is None
    assert not stats["Describe 988"]["suppressed"]
    assert stats["Describe 988"]["mean_change"] == 0


def test_filters_intersect_and_keep_end_date():
    d, _ = clean(row(training_date="2026-01-05"), row(county="Montgomery"),
                 row(language="Spanish"), row(training_date="2026-01-06"))
    filtered = p.filter_survey(d, counties=["Fairfax"], languages=["English"],
                               roles=["Student"], start_date="2026-01-05", end_date="2026-01-05")
    assert len(filtered) == 1
    assert len(p.filter_survey(d)) == 4


def test_empty_selection_has_safe_undefined_metrics():
    d, _ = clean(row())
    empty = p.filter_survey(d, counties=["No matching county"])
    summary = p.build_summary(empty)
    assert summary["overview"]["survey_rows"] == 0
    assert summary["overview"]["willingness_response_rate"] is None
    assert summary["knowledge"]["topics"]["Identify crisis"]["mean_change"] is None
    json.dumps(summary, allow_nan=False)


def test_export_contains_aggregates_not_comments_or_identifiers(tmp_path):
    d, _ = clean(row(id="PRIVATE-ID-MARKER", valuable_feedback="PRIVATE-COMMENT-MARKER"))
    path = p.export_summary(d, tmp_path / "summary.json")
    text = path.read_text(encoding="utf-8")
    exported = json.loads(text)
    assert exported["overview"]["survey_rows"] == 1
    assert "PRIVATE-ID-MARKER" not in text
    assert "PRIVATE-COMMENT-MARKER" not in text
    assert "valuable_feedback_raw" not in text


def test_pipeline_in_memory_end_to_end():
    result = p.run_pipeline(workbook_bytes(pd.DataFrame([row()])))
    assert result.raw_df.shape == (1, 20)
    assert result.summary["overview"]["survey_rows"] == 1
    assert result.quality["original_row_count"] == 1


@pytest.fixture
def app_module():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    import app
    return app


def test_optional_module_absent_vs_broken(app_module, monkeypatch):
    def absent(_):
        raise ModuleNotFoundError("missing", name="gap_detector")
    monkeypatch.setattr(app_module.importlib, "import_module", absent)
    assert app_module.load_optional_module("Gap Detector")[1] == "missing"
    def broken(_):
        raise ModuleNotFoundError("missing dependency", name="missing_dependency")
    monkeypatch.setattr(app_module.importlib, "import_module", broken)
    assert app_module.load_optional_module("Gap Detector")[1] == "broken"


def test_missing_function_is_contract_error(app_module, monkeypatch):
    monkeypatch.setattr(app_module.importlib, "import_module", lambda _: SimpleNamespace())
    assert app_module.load_optional_module("Gap Detector")[1] == "contract_error"


def test_finding_schema_and_private_evidence(app_module):
    finding = dict(id="synthetic", source="test", type="test", title="Demo finding",
                   description="An aggregate finding.", count=1, denominator=2,
                   percentage=50, limitations=["Synthetic"], evidence={"private": "Do not forward"})
    assert app_module.validate_findings({"findings": [finding]})[0]["evidence"] == {}
    finding["percentage"] = 150
    with pytest.raises(ValueError):
        app_module.validate_findings({"findings": [finding]})


def test_app_starts_and_all_navigation_survives_missing_team_modules(app_module, monkeypatch):
    from streamlit.testing.v1 import AppTest
    for module, _ in app_module.MODULES.values():
        monkeypatch.setitem(sys.modules, module, None)
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    assert not at.exception
    assert at.metric[0].value == "180"
    assert any("SYNTHETIC" in warning.value for warning in at.warning)
    for page in app_module.PAGES[1:]:
        at.sidebar.radio(key="workspace_page").set_value(page).run()
        assert not at.exception
        assert any("progress" in message.value for message in at.info)


def test_app_filters_change_the_same_dashboard_counts(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.multiselect(key="filter_counties").set_value(["Fairfax"]).run()
    assert not at.exception
    assert at.metric[0].value == "45"
    at.sidebar.multiselect(key="filter_roles").set_value(["Student"]).run()
    assert not at.exception
    assert any("No survey rows match" in message.value for message in at.info)


def test_app_upload_mode_has_safe_empty_state(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.radio(key="source_mode").set_value("Upload survey workbook").run()
    assert not at.exception
    assert any("Choose your survey" in message.value for message in at.info)


def test_app_upload_replacement_and_bad_schema_clear_old_results(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.radio(key="source_mode").set_value("Upload survey workbook").run()
    if not hasattr(at, "file_uploader") or not hasattr(at.file_uploader[0], "set_value"):
        pytest.skip("This Streamlit version does not simulate file uploads.")
    content = workbook_bytes(pd.DataFrame([row(), row(id="second")])).getvalue()
    at.file_uploader[0].set_value(("synthetic.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.metric[0].value == "2"
    # Replacement workbooks must produce new counts, not stale cached results.
    replacement = workbook_bytes(pd.DataFrame([row(county="Montgomery")])).getvalue()
    at.file_uploader[0].set_value(("replacement.xlsx", replacement, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.metric[0].value == "1"
    bad = workbook_bytes(pd.DataFrame({"wrong": ["test"]})).getvalue()
    at.file_uploader[0].set_value(("bad.xlsx", bad, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")).run()
    assert not at.exception
    assert at.error
    assert not at.metric
    assert "uploaded_result" not in at.session_state


def test_app_date_and_group_controls(app_module):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).with_name("app.py")), default_timeout=30).run()
    at.sidebar.checkbox(key="filter_dates_enabled").check().run()
    assert not at.exception
    assert at.metric[0].value == "175"  # Five synthetic rows have invalid dates.
    for field in ["role", "language"]:
        at.selectbox(key="comparison_group").set_value(field).run()
        at.selectbox(key="coverage_group").set_value(field).run()
        assert not at.exception
