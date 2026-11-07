import pandas as pd
import pytest

from gap_detector import (
    knowledge_summary,
    willingness_summary,
    knowledge_vs_willingness,
    subgroup_summary,
    detect_findings
)

from sample_data import create_sample_data


def test_knowledge_summary():
    df = create_sample_data()
    result = knowledge_summary(df)

    assert len(result) == 3
    assert result.loc[0, "paired_n"] == 4


def test_willingness_summary():
    df = create_sample_data()
    result = willingness_summary(df)

    assert result["total_responses"] == 4
    assert result["answered"] == 3
    assert result["missing"] == 1


def test_knowledge_vs_willingness():
    df = create_sample_data()
    result = knowledge_vs_willingness(df)

    assert result["complete_case_n"] == 3
    assert result["excluded_n"] == 1


def test_subgroup_summary():
    df = create_sample_data()
    result = subgroup_summary(df, "language")

    assert len(result) == 2
    assert all(result["sample_warning"] != "")


def test_detect_findings():
    df = create_sample_data()
    result = detect_findings(df)

    assert len(result) > 0
    assert all("evidence" in finding for finding in result)
    assert all("limitation" in finding for finding in result)

def test_empty_data():
    df = create_sample_data().iloc[0:0].copy()

    knowledge = knowledge_summary(df)
    willingness = willingness_summary(df)
    comparison = knowledge_vs_willingness(df)
    findings = detect_findings(df)

    assert all(knowledge["paired_n"] == 0)
    assert willingness["total_responses"] == 0
    assert comparison["complete_case_n"] == 0
    assert len(findings) == 1

def test_multiple_roles():
    df = create_sample_data()
    result = subgroup_summary(df, "role_list")

    # A participant can belong to more than one role
    assert result["total_n"].sum() > len(df)

    # Each role should be counted separately
    assert "staff" in result["group"].values
    assert "student" in result["group"].values

def test_missing_knowledge_answers():
    df = create_sample_data()

    # Remove all answers for one knowledge topic
    df["before_identify"] = None
    df["after_identify"] = None

    result = knowledge_summary(df)

    # No complete pairs should be counted for this topic
    assert result.loc[0, "paired_n"] == 0
    assert result.loc[0, "missing_pairs"] == len(df)

def test_small_group_warning():
    df = create_sample_data()
    result = subgroup_summary(df, "language")

    # All groups in our synthetic dataset have fewer than 20 people
    assert all(
        result["sample_warning"] == "Small sample: descriptive only"
    )

def test_constant_willingness():
    df = create_sample_data()

    df["willingness_to_call"] = [5, 5, 5, 5]

    result = knowledge_vs_willingness(df)

    # Correlation cannot be calculated when willingness never varies
    assert pd.isna(result["spearman_correlation"])