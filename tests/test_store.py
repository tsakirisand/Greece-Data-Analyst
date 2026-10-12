from __future__ import annotations

from pathlib import Path
import pytest

from greek_data_monitor.ingestion import Observation
from greek_data_monitor.quality import Finding
from greek_data_monitor.store import (
    get_connection,
    get_latest_observations,
    get_run_details,
    init_db,
    list_runs,
    save_run,
)


def _make_obs(period: int, value: float | None, status: str | None = None) -> Observation:
    return Observation(
        period=period,
        value=value,
        source_status=status,
        dataset="nama_10_gdp",
        dimensions={"geo": "EL", "na_item": "B1GQ", "unit": "CP_MEUR"},
        unit="CP_MEUR",
        retrieved_at="2026-10-12T18:00:00Z",
        source_url="https://example.com/test",
    )


def test_init_db_in_memory() -> None:
    conn = get_connection(":memory:")
    init_db(conn)
    tables = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    assert "quality_runs" in tables
    assert "observations" in tables
    assert "quality_findings" in tables
    assert "series_metadata" in tables


def test_save_run_and_query_snapshot(tmp_path: Path) -> None:
    db_file = tmp_path / "monitor_test.db"
    db_url = f"sqlite:///{db_file}"

    obs = [
        _make_obs(2021, 184574.6),
        _make_obs(2022, 207008.7, "p"),
    ]
    findings = [
        Finding("PASS", "all_rules", "Observations passed quality checks"),
    ]

    run_id = save_run(db_url, obs, findings)
    assert run_id == 1

    # Verify latest observations retrieval
    latest = get_latest_observations(db_url)
    assert len(latest) == 2
    assert latest[0].period == 2021
    assert latest[0].value == 184574.6
    assert latest[1].period == 2022
    assert latest[1].value == 207008.7
    assert latest[1].source_status == "p"
    assert latest[1].dataset == "nama_10_gdp"
    assert latest[1].dimensions["geo"] == "EL"


def test_repeated_runs_preserve_historical_snapshots(tmp_path: Path) -> None:
    db_file = tmp_path / "monitor_test.db"
    db_url = f"sqlite:///{db_file}"

    # Run 1: 2022 is provisional 200000.0
    obs_run1 = [_make_obs(2022, 200000.0, "p")]
    findings1 = [Finding("PASS", "all_rules", "Run 1 passed")]
    id1 = save_run(db_url, obs_run1, findings1)

    # Run 2: 2022 is revised to 207008.7
    obs_run2 = [_make_obs(2022, 207008.7, None)]
    findings2 = [
        Finding(
            "WARN",
            "data_revision",
            "Revised 2022 from 200000.0 to 207008.7",
            period=2022,
        )
    ]
    id2 = save_run(db_url, obs_run2, findings2)

    assert id1 == 1
    assert id2 == 2

    # Query runs list
    runs = list_runs(db_url)
    assert len(runs) == 2
    assert runs[0]["id"] == 2
    assert runs[0]["status"] == "WARN"
    assert runs[0]["warning_count"] == 1
    assert runs[1]["id"] == 1
    assert runs[1]["status"] == "PASS"

    # Verify run details for run 1
    details1 = get_run_details(db_url, id1)
    assert details1 is not None
    assert details1["observations"][0]["value"] == 200000.0
    assert details1["observations"][0]["source_status"] == "p"

    # Verify run details for run 2
    details2 = get_run_details(db_url, id2)
    assert details2 is not None
    assert details2["observations"][0]["value"] == 207008.7
    assert details2["observations"][0]["source_status"] is None
    assert len(details2["findings"]) == 1
    assert details2["findings"][0]["rule"] == "data_revision"

    # Latest observations should reflect run 2
    latest = get_latest_observations(db_url)
    assert latest[0].value == 207008.7


def test_get_run_details_not_found(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'missing.db'}"
    details = get_run_details(db_url, 999)
    assert details is None


def test_database_url_formats(tmp_path: Path) -> None:
    # Test sqlite:// prefix without triple slash
    db_url1 = f"sqlite://{tmp_path / 'test1.db'}"
    run_id1 = save_run(db_url1, [_make_obs(2020, 100.0)], [Finding("PASS", "all", "ok")])
    assert run_id1 == 1

    # Test plain path string
    db_url2 = str(tmp_path / "test2.db")
    run_id2 = save_run(db_url2, [_make_obs(2020, 100.0)], [Finding("PASS", "all", "ok")])
    assert run_id2 == 1
