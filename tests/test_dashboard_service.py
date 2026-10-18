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


def test_format_indicator_value() -> None:
    from greek_data_monitor.dashboard_service import format_indicator_value

    assert format_indicator_value(None) == "— (Missing)"
    assert format_indicator_value(248353.7, unit="CP_MEUR", unit_short="€M") == "€248,353.7 M"
    assert format_indicator_value(8.9, unit="PC_ACT", unit_short="%") == "8.90%"
    assert format_indicator_value(81.9, unit="YR", unit_short="years") == "81.9 yrs"
    assert format_indicator_value(10372335.0, unit="NR", unit_short="pers.") == "10.37 M"
    assert format_indicator_value(132149.0, unit="NR", unit_short="pers.") == "132,149"
    assert format_indicator_value(16.34, unit="MTOE", unit_short="MTOE") == "16.34 MTOE"
    assert format_indicator_value(68805.23, unit="THS_T", unit_short="kt CO2e") == "68,805.2 kt"
    assert format_indicator_value(178.39, unit="I15_A_AVG", unit_short="idx") == "178.39"


def test_calculate_safe_comparison_compatible_units() -> None:
    from greek_data_monitor.dashboard_service import calculate_safe_comparison

    obs_a = [{"period": 2020, "value": 17.6}, {"period": 2021, "value": 14.8}]
    obs_b = [{"period": 2020, "value": 15.5}, {"period": 2021, "value": 14.8}]
    meta_a = {"name": "Unemployment", "unit_short": "%"}
    meta_b = {"name": "Youth Unemployment", "unit_short": "%"}

    res = calculate_safe_comparison(obs_a, meta_a, obs_b, meta_b)
    assert res["compatible_raw"] is True
    assert res["requires_indexing"] is False
    assert len(res["data"]) == 2
    assert "Matching units" in res["message"]


def test_calculate_safe_comparison_incompatible_units_triggers_indexing() -> None:
    from greek_data_monitor.dashboard_service import calculate_safe_comparison

    obs_a = [{"period": 2020, "value": 167539.5}, {"period": 2021, "value": 184574.6}]
    obs_b = [{"period": 2020, "value": 17.6}, {"period": 2021, "value": 14.8}]
    meta_a = {"name": "GDP", "unit_short": "€M"}
    meta_b = {"name": "Unemployment", "unit_short": "%"}

    res = calculate_safe_comparison(obs_a, meta_a, obs_b, meta_b)
    assert res["compatible_raw"] is False
    assert res["requires_indexing"] is True
    assert len(res["data"]) == 2
    assert res["data"][0]["index_a"] == 100.0
    assert res["data"][0]["index_b"] == 100.0
    assert res["data"][1]["index_a"] > 100.0
    assert res["data"][1]["index_b"] < 100.0
    assert "re-indexed (Base 2020 = 100)" in res["message"]


def test_calculate_quality_scorecard_with_known_missing_periods() -> None:
    obs = [
        {"period": 2001, "value": 20.0},
        {"period": 2002, "value": None},  # Documented EU-SILC gap
        {"period": 2003, "value": 20.7},
    ]
    findings = [
        {"severity": "INFO", "rule": "known_structural_gap", "period": 2002, "message": "Documented EU-SILC gap"},
    ]
    card = calculate_quality_scorecard(
        obs,
        findings,
        min_year=1995,
        known_missing_periods={2002: "Documented EU-SILC transition gap"},
    )
    # The known gap should NOT penalize completeness or count as an error
    assert card["completeness_score"] == 100.0
    assert card["error_count"] == 0
    assert card["overall_score"] == 100.0
    assert card["grade"] == "A+"


def test_calculate_safe_comparison_zero_and_near_zero_base_values() -> None:
    from greek_data_monitor.dashboard_service import calculate_safe_comparison

    # Base year 2020 has 0.0 for series B
    obs_a = [{"period": 2020, "value": 100.0}, {"period": 2021, "value": 120.0}]
    obs_b_zero = [{"period": 2020, "value": 0.0}, {"period": 2021, "value": 10.0}]
    meta_a = {"name": "GDP", "unit_short": "€M"}
    meta_b = {"name": "Emissions", "unit_short": "kt"}

    res = calculate_safe_comparison(obs_a, meta_a, obs_b_zero, meta_b, base_year=2020)
    assert res["requires_indexing"] is True
    assert res["indexing_disabled"] is True
    assert "zero" in res["message"].lower()
    assert res["error_explanation"] is not None
    # Data is still returned without crash
    assert len(res["data"]) == 2
    assert res["data"][0]["index_a"] is None
    assert res["data"][0]["index_b"] is None

    # Base year 2020 has near-zero (1e-8) for series A
    obs_a_near_zero = [{"period": 2020, "value": 1e-8}, {"period": 2021, "value": 5.0}]
    obs_b = [{"period": 2020, "value": 10.0}, {"period": 2021, "value": 12.0}]
    res_near = calculate_safe_comparison(obs_a_near_zero, meta_a, obs_b, meta_b, base_year=2020)
    assert res_near["indexing_disabled"] is True
    assert "near-zero" in res_near["message"].lower()


def test_calculate_safe_comparison_missing_and_non_finite_base_values() -> None:
    import math
    from greek_data_monitor.dashboard_service import calculate_safe_comparison

    meta_a = {"name": "Series A", "unit_short": "A"}
    meta_b = {"name": "Series B", "unit_short": "B"}

    # Base value is None (missing)
    obs_a_none = [{"period": 2020, "value": None}, {"period": 2021, "value": 10.0}]
    obs_b = [{"period": 2020, "value": 50.0}, {"period": 2021, "value": 60.0}]
    res_none = calculate_safe_comparison(obs_a_none, meta_a, obs_b, meta_b, base_year=2020)
    assert res_none["indexing_disabled"] is True
    assert "missing" in res_none["message"].lower()

    # Base value is NaN
    obs_a_nan = [{"period": 2020, "value": float("nan")}, {"period": 2021, "value": 10.0}]
    res_nan = calculate_safe_comparison(obs_a_nan, meta_a, obs_b, meta_b, base_year=2020)
    assert res_nan["indexing_disabled"] is True
    assert "non-finite" in res_nan["message"].lower()

    # Base value is Inf
    obs_b_inf = [{"period": 2020, "value": float("inf")}, {"period": 2021, "value": 60.0}]
    obs_a = [{"period": 2020, "value": 100.0}, {"period": 2021, "value": 110.0}]
    res_inf = calculate_safe_comparison(obs_a, meta_a, obs_b_inf, meta_b, base_year=2020)
    assert res_inf["indexing_disabled"] is True
    assert "non-finite" in res_inf["message"].lower()


def test_calculate_safe_comparison_compatible_units_remains_available_with_zero() -> None:
    from greek_data_monitor.dashboard_service import calculate_safe_comparison

    # When units match, raw comparison is available even if a value is 0.0
    obs_a = [{"period": 2020, "value": 0.0}, {"period": 2021, "value": 2.5}]
    obs_b = [{"period": 2020, "value": 1.0}, {"period": 2021, "value": 3.0}]
    meta_a = {"name": "Inflation", "unit_short": "%"}
    meta_b = {"name": "Target", "unit_short": "%"}

    res = calculate_safe_comparison(obs_a, meta_a, obs_b, meta_b, base_year=2020)
    assert res["compatible_raw"] is True
    assert res["requires_indexing"] is False
    assert len(res["data"]) == 2
    assert "Matching units" in res["message"]



def test_sync_all_indicators_independent_failure(tmp_path: Any) -> None:
    from unittest.mock import MagicMock, patch
    from greek_data_monitor.catalog import IndicatorDefinition
    from greek_data_monitor.dashboard_service import sync_all_indicators
    from greek_data_monitor.ingestion import IngestionError, Observation

    db_url = f"sqlite:///{tmp_path / 'sync_test.db'}"

    mock_inds = [
        IndicatorDefinition(
            indicator_id="ind_ok",
            series_id="eurostat.test.ok",
            name="Working Series",
            topic="Economy",
            topic_icon="🏛️",
            unit="EUR",
            unit_short="€",
            frequency="Annual",
            source_name="Eurostat",
            source_url="http://example.com",
            api_url="http://example.com/api",
            dataset_code="test_ok",
            series_key="A.EUR.EL",
            dimensions={},
            description="desc",
            methodology="meth",
            limitations="none",
        ),
        IndicatorDefinition(
            indicator_id="ind_err",
            series_id="eurostat.test.fail",
            name="Failing Series",
            topic="Energy & Environment",
            topic_icon="⚡",
            unit="KW",
            unit_short="kW",
            frequency="Annual",
            source_name="Eurostat",
            source_url="http://example.com",
            api_url="http://example.com/fail_api",
            dataset_code="test_fail",
            series_key="A.KW.EL",
            dimensions={},
            description="desc",
            methodology="meth",
            limitations="none",
        ),
    ]

    def mock_fetch(series: Any, timeout: int = 30) -> list[Observation]:
        if series.indicator_id == "ind_ok":
            return [Observation(2021, 100.0), Observation(2022, 105.0)]
        raise IngestionError("Upstream service timed out")

    with patch("greek_data_monitor.ingestion.fetch_eurostat_series", side_effect=mock_fetch):
        res = sync_all_indicators(db_url, indicators=mock_inds)

    assert res["total"] == 2
    assert res["success"] == 1
    assert res["failed"] == 1
    assert res["details"][0]["status"] == "SUCCESS"
    assert res["details"][1]["status"] == "ERROR"
    assert "Upstream service timed out" in res["details"][1]["error_message"]


def test_get_overview_kpis_headline_and_all(tmp_path: Any) -> None:
    from greek_data_monitor.catalog import INDICATOR_CATALOG
    from greek_data_monitor.dashboard_service import get_overview_kpis
    from greek_data_monitor.store import init_db

    db_path = tmp_path / "overview_test.db"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)

    # Empty DB
    all_kpis = get_overview_kpis(db_url, headline_only=False)
    headline_kpis = get_overview_kpis(db_url, headline_only=True)

    assert len(all_kpis) == len(INDICATOR_CATALOG)
    assert len(headline_kpis) == 9
    assert all(k["has_data"] is False for k in all_kpis)
    assert any(k["is_headline"] is True for k in all_kpis)
    assert any(k["is_headline"] is False for k in all_kpis)


def test_calculate_indicator_correlation_matrix(tmp_path: Any) -> None:
    from greek_data_monitor.dashboard_service import calculate_indicator_correlation_matrix
    from greek_data_monitor.ingestion import Observation
    from greek_data_monitor.store import init_db, save_run

    db_path = tmp_path / "corr_test.db"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)

    # Insert 6 periods for two series
    obs1 = [Observation(2015 + i, 100.0 + i * 10) for i in range(6)]
    obs2 = [Observation(2015 + i, 50.0 + i * 5) for i in range(6)]

    save_run(db_url, obs1, [], series_id="eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR")
    save_run(db_url, obs2, [], series_id="eurostat.une_rt_a.EL.Y15-74.PC_ACT.T")

    res = calculate_indicator_correlation_matrix(
        db_url,
        indicator_ids=["gdp_nominal", "unemployment_rate"],
        min_periods=5,
    )
    assert len(res["indicators"]) == 2
    assert res["common_periods_count"] == 6
    # Perfect positive correlation 1.0
    assert res["correlation_matrix"][0][0] == 1.0
    assert res["correlation_matrix"][0][1] == 1.0




@pytest.mark.parametrize(('indicator_id', 'value', 'expected'), [
    ('energy_consumption', 16.34, '16.34 MTOE'),
    ('gdp_nominal', 248353.7, '€248,353.7 M'),
    ('ghg_emissions', 68805.23, '68,805.2 kt'),
    ('life_expectancy', 81.9, '81.9 yrs'),
    ('house_price_index', 178.39, '178.39'),
])
def test_format_full_catalog_units(indicator_id, value, expected):
    from greek_data_monitor.catalog import CATALOG_BY_ID
    from greek_data_monitor.dashboard_service import format_indicator_value
    indicator = CATALOG_BY_ID[indicator_id]
    assert format_indicator_value(value, indicator.unit, indicator.unit_short) == expected


@pytest.mark.parametrize(('previous', 'latest', 'metric', 'value', 'unit'), [
    (3.0, 2.9, 'percentage_points', -0.1, 'pp'),
    (10.1, 8.9, 'percentage_points', -1.2, 'pp'),
    (154.2, 146.1, 'percentage_points', -8.1, 'pp'),
    (0.0, 1.2, 'percentage_points', 1.2, 'pp'),
    (100.0, 110.0, 'relative_percent', 10.0, '%'),
    (-2.0, -1.0, 'relative_percent', 50.0, '%'),
    (0.0, 1.0, 'relative_percent', None, '%'),
    (1e-8, 1.0, 'relative_percent', None, '%'),
    (100.0, 110.0, 'disabled', None, '%'),
    (None, 110.0, 'relative_percent', None, '%'),
    (100.0, float('inf'), 'relative_percent', None, '%'),
])
def test_annual_change_metrics(previous, latest, metric, value, unit):
    from greek_data_monitor.dashboard_service import calculate_annual_change
    from greek_data_monitor.ingestion import Observation
    change = calculate_annual_change(Observation(2025, latest), Observation(2024, previous), metric)
    assert change['unit'] == unit
    if value is None:
        assert change['value'] is None
        assert change['display'] == '—'
    else:
        assert change['value'] == pytest.approx(value)
        assert unit in change['display']


def test_annual_change_does_not_bridge_missing_years():
    from greek_data_monitor.dashboard_service import calculate_annual_change
    from greek_data_monitor.ingestion import Observation
    assert calculate_annual_change(Observation(2025, 120), Observation(2023, 100))['value'] is None


def test_source_status_preserves_combined_flags_and_uncertainty():
    from greek_data_monitor.dashboard_service import format_source_status
    assert format_source_status('ep') == 'Estimated · Provisional'
    assert format_source_status('p') == 'Provisional'
    assert format_source_status(None) == 'Stored · No source flag'
    assert format_source_status(None, False) == 'No data'


def test_retrieval_age_uses_elapsed_time_not_year_string():
    from datetime import datetime, timezone
    from greek_data_monitor.dashboard_service import format_check_age
    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    assert format_check_age('2026-10-18T11:00:00Z', now) == 'Checked <24h ago'
    assert format_check_age('2026-10-17T12:00:00Z', now) == 'Checked 1 day ago'
    assert format_check_age('2026-10-15T12:00:00', now) == 'Checked 3 days ago'
    assert format_check_age('2026-10-19T12:00:00Z', now) == 'Future check timestamp'
    assert format_check_age('invalid', now) == 'Unknown check time'
    assert format_check_age(None, now) == 'Not checked'


def test_overview_uses_catalog_change_metric_and_source_flag(tmp_path):
    from greek_data_monitor.catalog import CATALOG_BY_ID
    from greek_data_monitor.dashboard_service import get_overview_kpis, get_what_changed_summary
    from greek_data_monitor.ingestion import Observation
    from greek_data_monitor.store import save_run
    db_url = f"sqlite:///{tmp_path / 'rates.db'}"
    indicator = CATALOG_BY_ID['inflation_rate']
    save_run(db_url, [Observation(2024, 3.0), Observation(2025, 2.9, source_status='p')], [], series_id=indicator.series_id)
    kpi = next(k for k in get_overview_kpis(db_url) if k['indicator_id'] == indicator.indicator_id)
    assert kpi['change_value'] == pytest.approx(-0.1)
    assert kpi['change_unit'] == 'pp'
    assert kpi['change_display'] == '-0.10 pp'
    assert kpi['data_status'] == 'Provisional'
    narrative = get_what_changed_summary(db_url)[0]['narrative']
    assert '-0.10 pp' in narrative
    assert '-3.3%' not in narrative
    assert 'Provisional' in narrative


def test_audit_report_uses_selected_indicator_metadata():
    from greek_data_monitor.catalog import CATALOG_BY_ID
    indicator = CATALOG_BY_ID['energy_consumption']
    score = calculate_quality_scorecard([{'period': 2024, 'value': 16.34}], [], min_year=indicator.start_year)
    report = generate_markdown_audit_report({'id': 1, 'series_id': indicator.series_id}, [], score, indicator.name, indicator=indicator)
    assert indicator.dataset_code in report
    assert indicator.api_url in report
    assert f'**Configured Coverage Start:** {indicator.start_year}' in report
    assert 'nama_10_gdp' not in report
    assert 'not ISO certification' in report


def test_score_without_active_observations_does_not_claim_perfect_quality():
    score = calculate_quality_scorecard([{'period': 1990, 'value': None}], [], min_year=2000)
    assert score['overall_score'] == 0
    assert score['grade'] == 'F'
    assert score['completeness_score'] == 0


def test_provisional_filter_includes_combined_source_flags():
    observations = [
        {'period': 2023, 'value': 150.0, 'source_status': 'e'},
        {'period': 2024, 'value': 165.0, 'source_status': 'p'},
        {'period': 2025, 'value': 178.0, 'source_status': 'ep'},
    ]
    assert [o['period'] for o in filter_and_sort_observations(observations, status_filter='Provisional only')] == [2024, 2025]
