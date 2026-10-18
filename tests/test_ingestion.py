from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from greek_data_monitor.config import DEFAULT_SERIES, SeriesConfig
from greek_data_monitor.ingestion import (
    IngestionError,
    Observation,
    fetch_eurostat_series,
    fetch_greek_gdp,
    parse_tsv,
)

SAMPLE_EUROSTAT_TSV = (
    "freq,unit,na_item,geo\\TIME_PERIOD\t1975 \t1976 \t1995 \t2022 \t2023 \t2024 \n"
    "A,CP_MEUR,B1GQ,EL\t: \t: u\t103206.4 \t207008.7 \t224686.2 p\t236736.0 \n"
)


def test_parse_tsv_success() -> None:
    obs = parse_tsv(SAMPLE_EUROSTAT_TSV, series=DEFAULT_SERIES)
    assert len(obs) == 6

    # Verify periods and sort order
    periods = [o.period for o in obs]
    assert periods == [1975, 1976, 1995, 2022, 2023, 2024]

    # 1975 has missing value ":" without flag
    assert obs[0].period == 1975
    assert obs[0].value is None
    assert obs[0].source_status is None

    # 1976 has missing value with status flag "u"
    assert obs[1].period == 1976
    assert obs[1].value is None
    assert obs[1].source_status == "u"

    # 1995 has numeric value 103206.4
    assert obs[2].period == 1995
    assert obs[2].value == 103206.4
    assert obs[2].source_status is None

    # 2023 has provisional flag "p"
    assert obs[4].period == 2023
    assert obs[4].value == 224686.2
    assert obs[4].source_status == "p"


def test_parse_tsv_preserves_metadata() -> None:
    cfg = SeriesConfig(
        series_id="test.series",
        dataset="nama_10_gdp",
        dimensions={"freq": "A", "unit": "CP_MEUR", "na_item": "B1GQ", "geo": "EL"},
        unit="CP_MEUR",
        description="Test series",
        source_url="https://example.com/test.tsv",
    )
    obs = parse_tsv(
        SAMPLE_EUROSTAT_TSV,
        series=cfg,
        retrieved_at="2026-10-12T18:00:00Z",
        source_url="https://example.com/test.tsv",
    )
    assert len(obs) > 0
    first = obs[0]
    assert first.dataset == "nama_10_gdp"
    assert first.unit == "CP_MEUR"
    assert first.retrieved_at == "2026-10-12T18:00:00Z"
    assert first.source_url == "https://example.com/test.tsv"
    assert first.dimensions["geo"] == "EL"
    assert first.dimensions["na_item"] == "B1GQ"


def test_parse_tsv_row_variant_and_commas() -> None:
    tsv_content = (
        "unit,geo\\time\tvalues\n"
        "2020\t167,539.5 b\n"
        "2021\t184574.6 \n"
        "2022\t: c\n"
    )
    obs = parse_tsv(tsv_content)
    assert len(obs) == 3
    assert obs[0].period == 2020
    assert obs[0].value == 167539.5
    assert obs[0].source_status == "b"

    assert obs[1].period == 2021
    assert obs[1].value == 184574.6

    assert obs[2].period == 2022
    assert obs[2].value is None
    assert obs[2].source_status == "c"


def test_parse_tsv_empty_raises_ingestion_error() -> None:
    with pytest.raises(IngestionError, match="empty response"):
        parse_tsv("")

    with pytest.raises(IngestionError, match="empty response"):
        parse_tsv("   \n\t\n  ")


def test_parse_tsv_invalid_header_raises_ingestion_error() -> None:
    with pytest.raises(IngestionError, match="Unexpected Eurostat TSV header"):
        parse_tsv("foo,bar\t1995\t1996\n1,2\t100\t200\n")


def test_parse_tsv_no_observations_raises_ingestion_error() -> None:
    with pytest.raises(IngestionError, match="no annual observations"):
        parse_tsv("freq,unit\\TIME_PERIOD\n")


@patch("greek_data_monitor.ingestion.requests.get")
def test_fetch_eurostat_series_success(mock_get: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_EUROSTAT_TSV
    mock_get.return_value = mock_resp

    obs = fetch_greek_gdp(timeout=10)
    assert len(obs) == 6
    assert mock_get.called
    assert mock_get.call_args[1]["timeout"] == 10


@patch("greek_data_monitor.ingestion.time.sleep")
@patch("greek_data_monitor.ingestion.requests.get")
def test_fetch_eurostat_series_timeout(mock_get: MagicMock, mock_sleep: MagicMock) -> None:
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    with pytest.raises(IngestionError, match="Timeout"):
        fetch_greek_gdp(timeout=5)


@patch("greek_data_monitor.ingestion.time.sleep")
@patch("greek_data_monitor.ingestion.requests.get")
def test_fetch_eurostat_series_http_error(mock_get: MagicMock, mock_sleep: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.reason = "Internal Server Error"
    mock_resp.text = "Server error occurred"
    mock_get.return_value = mock_resp

    with pytest.raises(IngestionError, match="Eurostat API returned HTTP 500"):
        fetch_greek_gdp(timeout=5)


@patch("greek_data_monitor.ingestion.time.sleep")
@patch("greek_data_monitor.ingestion.requests.get")
def test_fetch_eurostat_series_network_error(mock_get: MagicMock, mock_sleep: MagicMock) -> None:
    mock_get.side_effect = requests.exceptions.ConnectionError("Name resolution failed")

    with pytest.raises(IngestionError, match="Network error"):
        fetch_greek_gdp(timeout=5)


def test_parse_retry_after() -> None:
    from greek_data_monitor.ingestion import parse_retry_after

    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("15") == 15.0
    assert parse_retry_after("2.5") == 2.5
    # Capped at 60s
    assert parse_retry_after("300") == 60.0
    assert parse_retry_after("invalid_header") is None


def test_http_get_with_retries_transient_503_recovers() -> None:
    from greek_data_monitor.ingestion import http_get_with_retries

    resp_503 = MagicMock()
    resp_503.status_code = 503
    resp_503.headers = {}

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.text = "success"

    slept: list[float] = []

    with patch("greek_data_monitor.ingestion.requests.get", side_effect=[resp_503, resp_200]) as mock_get:
        resp = http_get_with_retries(
            "https://example.com/api",
            max_retries=2,
            backoff_factor=0.1,
            sleeper=lambda s: slept.append(s),
        )
        assert resp.status_code == 200
        assert mock_get.call_count == 2
        assert len(slept) == 1
        assert slept[0] >= 0.1  # backoff delay applied


def test_http_get_with_retries_respects_retry_after() -> None:
    from greek_data_monitor.ingestion import http_get_with_retries

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "4.5"}

    resp_200 = MagicMock()
    resp_200.status_code = 200

    slept: list[float] = []

    with patch("greek_data_monitor.ingestion.requests.get", side_effect=[resp_429, resp_200]) as mock_get:
        resp = http_get_with_retries(
            "https://example.com/api",
            max_retries=2,
            sleeper=lambda s: slept.append(s),
        )
        assert resp.status_code == 200
        assert mock_get.call_count == 2
        assert len(slept) == 1
        assert slept[0] == 4.5  # Exactly parsed Retry-After header


def test_http_get_with_retries_permanent_404_and_400_not_retried() -> None:
    from greek_data_monitor.ingestion import http_get_with_retries

    resp_404 = MagicMock()
    resp_404.status_code = 404
    resp_404.headers = {}

    slept: list[float] = []

    with patch("greek_data_monitor.ingestion.requests.get", return_value=resp_404) as mock_get:
        resp = http_get_with_retries(
            "https://example.com/api",
            max_retries=3,
            sleeper=lambda s: slept.append(s),
        )
        assert resp.status_code == 404
        # MUST NOT retry permanent client error
        assert mock_get.call_count == 1
        assert len(slept) == 0

    resp_400 = MagicMock()
    resp_400.status_code = 400
    with patch("greek_data_monitor.ingestion.requests.get", return_value=resp_400) as mock_get_400:
        resp = http_get_with_retries(
            "https://example.com/api",
            max_retries=3,
            sleeper=lambda s: slept.append(s),
        )
        assert resp.status_code == 400
        assert mock_get_400.call_count == 1
        assert len(slept) == 0


def test_http_get_with_retries_exhausted_retries_raises_ingestion_error() -> None:
    from greek_data_monitor.ingestion import http_get_with_retries

    slept: list[float] = []
    with patch(
        "greek_data_monitor.ingestion.requests.get",
        side_effect=requests.exceptions.ConnectionError("Connection refused"),
    ) as mock_get:
        with pytest.raises(IngestionError, match="Network error .* after 2 retries"):
            http_get_with_retries(
                "https://example.com/api",
                max_retries=2,
                sleeper=lambda s: slept.append(s),
            )
        assert mock_get.call_count == 3
        assert len(slept) == 2
