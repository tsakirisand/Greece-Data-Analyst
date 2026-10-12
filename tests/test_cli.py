from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from greek_data_monitor.cli import main
from greek_data_monitor.ingestion import IngestionError, Observation

SAMPLE_TSV_PASS = (
    "freq,unit,na_item,geo\\TIME_PERIOD\t2020\t2021\t2022\n"
    "A,CP_MEUR,B1GQ,EL\t167539.5\t184574.6\t207008.7\n"
)

SAMPLE_TSV_WARN = (
    "freq,unit,na_item,geo\\TIME_PERIOD\t2020\t2021\n"
    "A,CP_MEUR,B1GQ,EL\t100000.0\t150000.0\n"  # +50% change
)

SAMPLE_TSV_ERROR = (
    "freq,unit,na_item,geo\\TIME_PERIOD\t2020\t2021\n"
    "A,CP_MEUR,B1GQ,EL\t167539.5\t: \n"  # Missing active observation
)


@patch("greek_data_monitor.cli.fetch_eurostat_series")
def test_cli_run_pass(mock_fetch: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_file = tmp_path / "cli_test.db"
    db_url = f"sqlite:///{db_file}"

    mock_fetch.return_value = [
        Observation(2020, 167539.5),
        Observation(2021, 184574.6),
    ]

    # Should exit cleanly (status 0)
    main(["run", "--db-url", db_url])
    captured = capsys.readouterr()
    assert "Greek Public Data Quality Monitor — Run #1" in captured.out
    assert "PASS" in captured.out


@patch("greek_data_monitor.cli.fetch_eurostat_series")
def test_cli_run_warning_does_not_fail(
    mock_fetch: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_file = tmp_path / "cli_warn_test.db"
    db_url = f"sqlite:///{db_file}"

    # +50% YoY change should trigger WARN, but NOT fail the run (exit code 0)
    mock_fetch.return_value = [
        Observation(2020, 100000.0),
        Observation(2021, 150000.0),
    ]

    main(["run", "--db-url", db_url, "--threshold", "30.0"])
    captured = capsys.readouterr()
    assert "Run #1" in captured.out
    assert "[WARN]" in captured.out
    assert "year_over_year_change" in captured.out


@patch("greek_data_monitor.cli.fetch_eurostat_series")
def test_cli_run_error_exits_with_code_2(
    mock_fetch: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_file = tmp_path / "cli_err_test.db"
    db_url = f"sqlite:///{db_file}"

    mock_fetch.return_value = [
        Observation(2020, 167539.5),
        Observation(2021, None),  # Missing observation in active series
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--db-url", db_url, "--min-year", "1995"])
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "[ERROR]" in captured.out
    assert "not_null" in captured.out


@patch("greek_data_monitor.cli.fetch_eurostat_series")
def test_cli_run_ingestion_failure_exits_with_code_1(
    mock_fetch: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_file = tmp_path / "cli_ingest_err.db"
    db_url = f"sqlite:///{db_file}"

    mock_fetch.side_effect = IngestionError("Eurostat network connection timed out")

    with pytest.raises(SystemExit) as exc_info:
        main(["run", "--db-url", db_url])
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Ingestion failed: Eurostat network connection timed out" in captured.err


@patch("greek_data_monitor.cli.fetch_eurostat_series")
def test_cli_history_command(
    mock_fetch: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_file = tmp_path / "cli_hist_test.db"
    db_url = f"sqlite:///{db_file}"

    mock_fetch.return_value = [
        Observation(2020, 167539.5),
        Observation(2021, 184574.6),
    ]

    # Run twice
    main(["run", "--db-url", db_url])
    main(["run", "--db-url", db_url])
    capsys.readouterr()  # clear run output

    # Check history list
    main(["history", "--db-url", db_url])
    captured = capsys.readouterr()
    assert "Recent Quality Runs" in captured.out
    assert "1" in captured.out
    assert "2" in captured.out

    # Check history for specific run ID
    main(["history", "--db-url", db_url, "--run-id", "1"])
    captured_details = capsys.readouterr()
    assert "Quality Run #1 Details" in captured_details.out
    assert "all_rules" in captured_details.out
