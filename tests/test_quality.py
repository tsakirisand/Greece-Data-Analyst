from __future__ import annotations

import pytest

from greek_data_monitor.ingestion import Observation
from greek_data_monitor.quality import Finding, inspect


def _make_obs(period: int, value: float | None, status: str | None = None) -> Observation:
    return Observation(period=period, value=value, source_status=status)


def test_inspect_clean_series_passes() -> None:
    obs = [
        _make_obs(2020, 167539.5),
        _make_obs(2021, 184574.6),
        _make_obs(2022, 207008.7),
    ]
    findings = inspect(obs, threshold_pct=30.0)
    assert len(findings) == 1
    assert findings[0].severity == "PASS"
    assert findings[0].rule == "all_rules"


def test_inspect_not_null_rule() -> None:
    obs = [
        _make_obs(1990, None),  # Pre-1995 coverage
        _make_obs(2020, 167539.5),
        _make_obs(2021, None),  # Missing active observation
    ]
    findings = inspect(obs, threshold_pct=30.0, min_year=1995)

    info_findings = [f for f in findings if f.rule == "pre_series_coverage"]
    assert len(info_findings) == 1
    assert info_findings[0].severity == "INFO"
    assert info_findings[0].period == 1990

    error_findings = [f for f in findings if f.rule == "not_null"]
    assert len(error_findings) == 1
    assert error_findings[0].severity == "ERROR"
    assert error_findings[0].period == 2021


def test_inspect_not_null_without_min_year() -> None:
    obs = [
        _make_obs(1990, None),
    ]
    findings = inspect(obs, threshold_pct=30.0, min_year=None)
    error_findings = [f for f in findings if f.rule == "not_null"]
    assert len(error_findings) == 1
    assert error_findings[0].severity == "ERROR"


def test_inspect_unique_period_rule() -> None:
    obs = [
        _make_obs(2020, 167539.5),
        _make_obs(2020, 167539.5),
        _make_obs(2021, 184574.6),
    ]
    findings = inspect(obs, threshold_pct=30.0)
    dup_findings = [f for f in findings if f.rule == "unique_period"]
    assert len(dup_findings) == 1
    assert dup_findings[0].severity == "ERROR"
    assert dup_findings[0].period == 2020


def test_inspect_valid_period_rule() -> None:
    obs = [
        _make_obs(1800, 100.0),
        _make_obs(2020, 167539.5),
        _make_obs(2500, 200.0),
    ]
    findings = inspect(obs, threshold_pct=30.0)
    invalid_findings = [f for f in findings if f.rule == "valid_period"]
    assert len(invalid_findings) == 2
    assert all(f.severity == "ERROR" for f in invalid_findings)


def test_inspect_year_over_year_change_warn_not_error() -> None:
    obs = [
        _make_obs(2020, 100000.0),
        _make_obs(2021, 150000.0),  # +50% change (exceeds 30%)
    ]
    findings = inspect(obs, threshold_pct=30.0)
    yoy_findings = [f for f in findings if f.rule == "year_over_year_change"]
    assert len(yoy_findings) == 1
    assert yoy_findings[0].severity == "WARN"
    assert yoy_findings[0].period == 2021
    assert yoy_findings[0].details["change_pct"] == 50.0
    # Crucial: warn must NOT be an error
    assert not any(f.severity == "ERROR" for f in findings)


def test_inspect_data_revision_rule() -> None:
    previous_obs = [
        _make_obs(2020, 167539.5, "p"),
        _make_obs(2021, 180000.0, "p"),
    ]
    current_obs = [
        _make_obs(2020, 167539.5, None),  # Flag changed from 'p' to finalized None
        _make_obs(2021, 184574.6, "f"),   # Value revised from 180000.0 to 184574.6
    ]

    findings = inspect(current_obs, threshold_pct=30.0, previous_observations=previous_obs)

    val_revisions = [f for f in findings if f.rule == "data_revision"]
    assert len(val_revisions) == 1
    assert val_revisions[0].severity == "WARN"
    assert val_revisions[0].period == 2021
    assert val_revisions[0].details["previous_value"] == 180000.0
    assert val_revisions[0].details["current_value"] == 184574.6

    status_revisions = [f for f in findings if f.rule == "status_revision"]
    assert len(status_revisions) == 1
    assert status_revisions[0].severity == "INFO"
    assert status_revisions[0].period == 2020


def test_inspect_empty_series() -> None:
    findings = inspect([])
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert findings[0].rule == "empty_series"


def test_inspect_percentage_points_measure() -> None:
    # Inflation moving from 0.6% to 9.3% is an 8.7 pp increase
    obs = [
        _make_obs(2021, 0.6),
        _make_obs(2022, 9.3),
    ]
    # With threshold 5.0 pp, 8.7 pp difference triggers WARN
    findings = inspect(obs, threshold_pct=5.0, change_metric="percentage_points")
    yoy_findings = [f for f in findings if f.rule == "year_over_year_change"]
    assert len(yoy_findings) == 1
    assert yoy_findings[0].severity == "WARN"
    assert "pp shift" in yoy_findings[0].message
    assert yoy_findings[0].details["change_pp"] == 8.7
    assert yoy_findings[0].details["metric"] == "percentage_points"

    # Moderate change (e.g. 1.2 to 2.5 = 1.3 pp) with 5.0 pp threshold passes
    obs_mod = [
        _make_obs(2021, 1.2),
        _make_obs(2022, 2.5),
    ]
    findings_mod = inspect(obs_mod, threshold_pct=5.0, change_metric="percentage_points")
    assert not any(f.rule == "year_over_year_change" for f in findings_mod)


def test_inspect_zero_and_near_zero_prior_value() -> None:
    # When prior value is exactly 0.0 or near-zero, relative % is undefined
    obs = [
        _make_obs(2020, 0.0),
        _make_obs(2021, 15.0),
    ]
    findings = inspect(obs, threshold_pct=30.0, change_metric="relative_percent")
    info_findings = [f for f in findings if f.rule == "year_over_year_change"]
    assert len(info_findings) == 1
    assert info_findings[0].severity == "INFO"
    assert "zero baseline" in info_findings[0].message
    assert info_findings[0].details["change_abs"] == 15.0


def test_inspect_negative_values_relative_percent() -> None:
    # Prior is negative (e.g. -2.0 to -1.0)
    obs = [
        _make_obs(2020, -2.0),
        _make_obs(2021, -1.0),
    ]
    findings = inspect(obs, threshold_pct=30.0, change_metric="relative_percent")
    yoy_findings = [f for f in findings if f.rule == "year_over_year_change"]
    assert len(yoy_findings) == 1
    assert yoy_findings[0].severity == "WARN"
    assert yoy_findings[0].details["change_pct"] == 50.0


def test_inspect_known_missing_periods_reports_info_not_error() -> None:
    # 2002 is a documented EU-SILC survey gap
    known_gaps = {2002: "Official EU-SILC survey transition gap"}
    obs = [
        _make_obs(2001, 20.0),
        _make_obs(2002, None),  # Documented missing year
        _make_obs(2003, 20.7, "b"),
        _make_obs(2021, None),  # Unexpected missing year
    ]
    findings = inspect(
        obs,
        min_year=1995,
        known_missing_periods=known_gaps,
    )

    gap_findings = [f for f in findings if f.rule == "known_structural_gap"]
    assert len(gap_findings) == 1
    assert gap_findings[0].severity == "INFO"
    assert gap_findings[0].period == 2002
    assert "Official EU-SILC" in gap_findings[0].message

    err_findings = [f for f in findings if f.rule == "not_null"]
    assert len(err_findings) == 1
    assert err_findings[0].severity == "ERROR"
    assert err_findings[0].period == 2021


def test_inspect_change_metric_disabled() -> None:
    obs = [
        _make_obs(2020, 10.0),
        _make_obs(2021, 500.0),
    ]
    findings = inspect(obs, threshold_pct=10.0, change_metric="disabled")
    assert not any(f.rule == "year_over_year_change" for f in findings)
