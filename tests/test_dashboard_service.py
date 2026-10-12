from __future__ import annotations

import pytest

from greek_data_monitor.dashboard_service import (
    calculate_quality_scorecard,
    calculate_statistical_anomalies,
    compare_run_snapshots,
    filter_and_sort_observations,
    format_gdp_value,
    generate_markdown_audit_report,
    get_flag_descriptions,
    get_greek_economic_milestones,
    get_quality_rule_descriptions,
)


def test_format_gdp_value() -> None:
    assert format_gdp_value(None) == "— (Missing)"
    assert format_gdp_value(248353.7) == "€248,353.7 M"


def test_get_quality_rule_descriptions() -> None:
    rules = get_quality_rule_descriptions()
    assert "not_null" in rules
    assert "year_over_year_change" in rules
    assert "valid_period" in rules
    assert "unique_period" in rules
    assert "data_revision" in rules
    assert "plain_explanation" in rules["not_null"]


def test_get_flag_descriptions() -> None:
    flags = get_flag_descriptions()
    assert ":" in flags
    assert "p" in flags
    assert "b" in flags


def test_compare_run_snapshots_identical() -> None:
    obs = [
        {"period": 2020, "value": 167539.5, "source_status": None},
        {"period": 2021, "value": 184574.6, "source_status": "p"},
    ]
    res = compare_run_snapshots(obs, obs)
    assert not res["has_changes"]
    assert res["unchanged_count"] == 2
    assert res["revised_count"] == 0
    assert res["added_count"] == 0
    assert res["removed_count"] == 0
    assert len(res["diffs"]) == 0


def test_compare_run_snapshots_revised_and_added() -> None:
    run1 = [
        {"period": 2020, "value": 167500.0, "source_status": "p"},
        {"period": 2021, "value": 180000.0, "source_status": "p"},
    ]
    run2 = [
        {"period": 2020, "value": 167539.5, "source_status": None},  # value revised & flag removed
        {"period": 2021, "value": 180000.0, "source_status": None},  # flag changed only
        {"period": 2022, "value": 207008.7, "source_status": "p"},   # newly added period
    ]
    res = compare_run_snapshots(run1, run2)
    assert res["has_changes"]
    assert res["revised_count"] == 2
    assert res["added_count"] == 1
    assert res["removed_count"] == 0

    diff_map = {d["period"]: d for d in res["diffs"]}
    assert diff_map[2020]["change_type"] == "Value Revised"
    assert diff_map[2020]["old_value"] == 167500.0
    assert diff_map[2020]["new_value"] == 167539.5

    assert diff_map[2021]["change_type"] == "Status Flag Changed"

    assert diff_map[2022]["change_type"] == "New Period Added"
    assert diff_map[2022]["new_value"] == 207008.7


def test_filter_and_sort_observations() -> None:
    obs = [
        {"period": 1990, "value": None, "source_status": ":", "raw_value": ":"},
        {"period": 2020, "value": 167539.5, "source_status": "b", "raw_value": "167539.5 b"},
        {"period": 2023, "value": 224686.2, "source_status": "p", "raw_value": "224686.2 p"},
        {"period": 2024, "value": 236736.0, "source_status": "p", "raw_value": "236736.0 p"},
    ]

    # Filter year range
    r1 = filter_and_sort_observations(obs, year_range=(2020, 2023))
    assert len(r1) == 2
    assert [x["period"] for x in r1] == [2020, 2023]

    # Filter numeric only
    r2 = filter_and_sort_observations(obs, status_filter="Numeric only")
    assert len(r2) == 3

    # Filter missing only
    r3 = filter_and_sort_observations(obs, status_filter="Missing values only")
    assert len(r3) == 1
    assert r3[0]["period"] == 1990

    # Filter provisional only
    r4 = filter_and_sort_observations(obs, status_filter="Provisional only")
    assert len(r4) == 2

    # Search filter
    r5 = filter_and_sort_observations(obs, search_term="2024")
    assert len(r5) == 1
    assert r5[0]["period"] == 2024

    # Sort descending by period
    r6 = filter_and_sort_observations(obs, sort_by="period", ascending=False)
    assert r6[0]["period"] == 2024
    assert r6[-1]["period"] == 1990


def test_calculate_quality_scorecard_clean() -> None:
    obs = [
        {"period": 1990, "value": None},  # Pre-1995, should not penalize completeness
        {"period": 2020, "value": 167539.5},
        {"period": 2021, "value": 184574.6},
    ]
    findings = [{"severity": "PASS", "rule": "all_rules", "message": "all good"}]
    card = calculate_quality_scorecard(obs, findings, min_year=1995)

    assert card["completeness_score"] == 100.0
    assert card["validity_score"] == 100.0
    assert card["uniqueness_score"] == 100.0
    assert card["plausibility_score"] == 100.0
    assert card["overall_score"] == 100.0
    assert card["grade"] == "A+"


def test_calculate_quality_scorecard_with_issues() -> None:
    obs = [
        {"period": 2020, "value": None},  # Active missing value
        {"period": 2021, "value": 184574.6},
    ]
    findings = [
        {"severity": "ERROR", "rule": "not_null", "message": "missing 2020"},
        {"severity": "WARN", "rule": "year_over_year_change", "message": "large change"},
    ]
    card = calculate_quality_scorecard(obs, findings, min_year=1995)
    assert card["completeness_score"] == 50.0
    assert card["plausibility_score"] == 85.0
    assert card["error_count"] == 1
    # Error cap should apply
    assert card["overall_score"] <= 65.0
    assert card["grade"] in ("C", "F")


def test_get_greek_economic_milestones() -> None:
    milestones = get_greek_economic_milestones()
    assert len(milestones) >= 5
    years = [m["year"] for m in milestones]
    assert 2001 in years
    assert 2009 in years
    assert 2020 in years


def test_calculate_statistical_anomalies() -> None:
    import pandas as pd
    df = pd.DataFrame(
        [
            {"period": 2018, "value": 100.0, "yoy_change_pct": 2.0},
            {"period": 2019, "value": 102.0, "yoy_change_pct": 2.0},
            {"period": 2020, "value": 70.0, "yoy_change_pct": -31.37},  # Extreme outlier
            {"period": 2021, "value": 72.0, "yoy_change_pct": 2.85},
            {"period": 2022, "value": 74.0, "yoy_change_pct": 2.78},
        ]
    )
    res = calculate_statistical_anomalies(df)
    assert len(res["anomalies"]) >= 1
    assert res["anomalies"][0]["period"] == 2020
    assert res["anomalies"][0]["direction"] == "Contraction"


def test_generate_markdown_audit_report() -> None:
    run_dict = {"id": 1, "checked_at": "2026-10-12T18:00:00Z", "status": "PASS", "observation_count": 51}
    findings = [{"severity": "PASS", "rule": "all_rules", "period": None, "message": "All passed"}]
    scorecard = {"overall_score": 98.5, "grade": "A+", "completeness_score": 100.0, "validity_score": 100.0, "uniqueness_score": 100.0, "plausibility_score": 100.0, "error_count": 0, "warning_count": 0, "active_period_count": 31}

    md = generate_markdown_audit_report(run_dict, findings, scorecard, "Eurostat Greek GDP")
    assert "Official Data Quality Audit Report" in md
    assert "Eurostat Greek GDP" in md
    assert "#1" in md
    assert "98.5/100" in md
    assert "A+" in md

