from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import random
import re
import time
from dataclasses import dataclass, field

import requests

from .config import DEFAULT_SERIES, SeriesConfig


class IngestionError(Exception):
    """Raised when data fetching or response parsing fails."""


@dataclass(frozen=True)
class Observation:
    period: int
    value: float | None
    source_status: str | None = None
    dataset: str = "nama_10_gdp"
    dimensions: dict[str, str] = field(default_factory=dict)
    unit: str = "CP_MEUR"
    retrieved_at: str = ""
    source_url: str = ""
    raw_value: str = ""


def parse_tsv(
    payload: str,
    series: SeriesConfig | None = None,
    retrieved_at: str | None = None,
    source_url: str | None = None,
) -> list[Observation]:
    """Parse Eurostat TSV response into structured Observation records.

    Handles standard Eurostat TSV formatting including missing value markers (':'),
    optional observation status flags (e.g., 'p', 'b', 'e'), dimension keys,
    and metadata attachment.
    """
    if not payload or not payload.strip():
        raise IngestionError("Eurostat returned an empty response")

    retrieved_ts = (
        retrieved_at
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    dataset_name = (
        getattr(series, "dataset", None)
        or getattr(series, "dataset_code", None)
        or "nama_10_gdp"
        if series
        else "nama_10_gdp"
    )
    default_unit = getattr(series, "unit", "CP_MEUR") if series else "CP_MEUR"
    default_dimensions = dict(getattr(series, "dimensions", {})) if series else {}
    resolved_source_url = source_url or (
        getattr(series, "api_url", None)
        or getattr(series, "source_url", "")
        if series
        else ""
    )

    rows = list(csv.reader(io.StringIO(payload), delimiter="\t"))
    if not rows:
        raise IngestionError("Eurostat returned an empty response")

    header = rows[0]
    if not header or not any(cell.strip() for cell in header):
        raise IngestionError("Eurostat response missing table header")

    first_col = header[0].strip().lower()
    if "time" not in first_col and "period" not in first_col:
        raise IngestionError(f"Unexpected Eurostat TSV header: {header!r}")

    # Extract dimension names from the first header cell (e.g. 'freq,unit,na_item,geo\TIME_PERIOD')
    dim_names: list[str] = []
    if "\\" in header[0]:
        dims_part = header[0].split("\\")[0].strip()
        if dims_part:
            dim_names = [d.strip() for d in dims_part.split(",") if d.strip()]

    observations: list[Observation] = []

    # Check if header contains period labels (standard matrix format)
    header_has_years = any(re.search(r"\b(\d{4})\b", col) for col in header[1:])

    for row in rows[1:]:
        if not row or not any(cell.strip() for cell in row):
            continue

        # Extract dimension values if row header matches dimension names
        row_dims = dict(default_dimensions)
        if dim_names and row[0].strip():
            row_dim_values = [v.strip() for v in row[0].split(",")]
            if len(row_dim_values) == len(dim_names):
                row_dims.update(dict(zip(dim_names, row_dim_values)))

        unit_val = row_dims.get("unit", default_unit)

        if header_has_years and len(row) == len(header):
            # Standard Eurostat matrix format: time periods in header, series values in data row
            for period_label, raw_cell in zip(header[1:], row[1:]):
                clean_label = period_label.strip()
                period_match = re.search(r"\b(\d{4})\b", clean_label)
                if not period_match:
                    continue
                period = int(period_match.group(1))

                val, status, raw_str = _parse_cell(raw_cell)
                observations.append(
                    Observation(
                        period=period,
                        value=val,
                        source_status=status,
                        dataset=dataset_name,
                        dimensions=row_dims,
                        unit=unit_val,
                        retrieved_at=retrieved_ts,
                        source_url=resolved_source_url,
                        raw_value=raw_str,
                    )
                )
        else:
            # Row-per-period variant where period is in row[0]
            clean_label = row[0].strip()
            period_match = re.search(r"\b(\d{4})\b", clean_label)
            if period_match:
                period = int(period_match.group(1))
                raw_cell = row[1] if len(row) > 1 else ""
                val, status, raw_str = _parse_cell(raw_cell)
                observations.append(
                    Observation(
                        period=period,
                        value=val,
                        source_status=status,
                        dataset=dataset_name,
                        dimensions=row_dims,
                        unit=unit_val,
                        retrieved_at=retrieved_ts,
                        source_url=resolved_source_url,
                        raw_value=raw_str,
                    )
                )

    if not observations:
        raise IngestionError("Eurostat response contained no annual observations")

    return sorted(observations, key=lambda item: item.period)


def _parse_cell(raw_cell: str) -> tuple[float | None, str | None, str]:
    """Parse individual cell containing optional number, flag, or missing marker."""
    raw_str = raw_cell.strip()
    if not raw_str:
        return None, None, ""

    if raw_str.startswith(":"):
        # Eurostat missing value marker, e.g. ':', ': u', ': c'
        parts = raw_str.split(None, 1)
        status = parts[1].strip() if len(parts) > 1 else None
        return None, status or None, raw_str

    parts = raw_str.split(None, 1)
    val_part = parts[0] if parts else ""
    status = parts[1].strip() if len(parts) > 1 else None

    try:
        val = float(val_part.replace(",", ""))
        return val, status or None, raw_str
    except ValueError:
        return None, status or None, raw_str


COUNTRY_NAMES: dict[str, str] = {
    "EL": "Greece",
    "EU27_2020": "European Union (EU-27)",
    "DE": "Germany",
    "IT": "Italy",
    "ES": "Spain",
    "PT": "Portugal",
    "CY": "Cyprus",
    "FR": "France",
}

COUNTRY_FLAGS: dict[str, str] = {
    "EL": "🇬🇷",
    "EU27_2020": "🇪🇺",
    "DE": "🇩🇪",
    "IT": "🇮🇹",
    "ES": "🇪🇸",
    "PT": "🇵🇹",
    "CY": "🇨🇾",
    "FR": "🇫🇷",
}


def parse_multi_country_tsv(
    payload: str,
    indicator_id: str = "",
    retrieved_at: str | None = None,
) -> list[dict[str, Any]]:
    """Parse Eurostat multi-country TSV into structured country benchmark records."""
    if not payload or not payload.strip():
        raise IngestionError("Eurostat returned an empty response")

    retrieved_ts = (
        retrieved_at
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )
    rows = list(csv.reader(io.StringIO(payload), delimiter="\t"))
    if not rows:
        raise IngestionError("Eurostat returned an empty response")

    header = rows[0]
    if not header or not any(cell.strip() for cell in header):
        raise IngestionError("Eurostat response missing table header")

    col_years: list[int] = []
    for col in header[1:]:
        m = re.search(r"\b(\d{4})\b", col.strip())
        col_years.append(int(m.group(1)) if m else -1)

    benchmarks: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        first_cell = row[0].strip()
        geo_code = first_cell.split(",")[-1].strip() if "," in first_cell else first_cell
        country_name = COUNTRY_NAMES.get(geo_code, geo_code)

        for year, raw_cell in zip(col_years, row[1:]):
            if year < 1900:
                continue
            val, status, _ = _parse_cell(raw_cell)
            benchmarks.append(
                {
                    "indicator_id": indicator_id,
                    "country_code": geo_code,
                    "country_name": country_name,
                    "period": year,
                    "value": val,
                    "source_status": status,
                    "fetched_at": retrieved_ts,
                }
            )

    return benchmarks


RETRIABLE_STATUS_CODES = {429, 502, 503, 504}


def parse_retry_after(header_val: str | None) -> float | None:
    """Parse HTTP Retry-After header into seconds (integer seconds or date format)."""
    if not header_val or not header_val.strip():
        return None
    header_val = header_val.strip()
    try:
        sec = float(header_val)
        return max(0.0, min(sec, 60.0))
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime
        target_dt = parsedate_to_datetime(header_val)
        now_dt = datetime.now(timezone.utc)
        diff = (target_dt - now_dt).total_seconds()
        return max(0.0, min(diff, 60.0))
    except Exception:
        return None


def http_get_with_retries(
    url: str,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    headers: dict[str, str] | None = None,
    sleeper: Any = time.sleep,
) -> requests.Response:
    """Execute HTTP GET with bounded exponential backoff, jitter, and Retry-After support.

    Retries on:
    - Transient network timeouts and connection resets
    - HTTP 429 (Rate Limited), 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)

    Non-retriable:
    - HTTP 400, 404, and other permanent client status codes return immediately without retrying.
    """
    req_headers = {"User-Agent": "GreekPublicDataQualityMonitor/0.1.0"}
    if headers:
        req_headers.update(headers)

    last_exc: Exception | None = None
    response: requests.Response | None = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers=req_headers)

            if response.status_code in RETRIABLE_STATUS_CODES and attempt < max_retries:
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                if retry_after is not None:
                    delay = retry_after
                else:
                    delay = backoff_factor * (2 ** attempt) + random.uniform(0.0, 0.1)
                sleeper(delay)
                continue

            return response

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = backoff_factor * (2 ** attempt) + random.uniform(0.0, 0.1)
                sleeper(delay)
                continue
            break
        except requests.exceptions.RequestException as exc:
            raise IngestionError(f"Network error fetching from {url}: {exc}") from exc

    if last_exc:
        if isinstance(last_exc, requests.exceptions.Timeout):
            raise IngestionError(
                f"Timeout ({timeout}s) fetching from {url} after {max_retries} retries"
            ) from last_exc
        raise IngestionError(
            f"Network error fetching from {url} after {max_retries} retries: {last_exc}"
        ) from last_exc

    if response is not None and response.status_code != 200:
        preview = response.text[:200].strip()
        raise IngestionError(
            f"Eurostat API returned HTTP {response.status_code} ({response.reason}) after {max_retries} retries: {preview}"
        )

    raise IngestionError(f"Failed to fetch data from {url} after {max_retries} retries")


def fetch_indicator_benchmarks(
    indicator_def: Any,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
) -> list[dict[str, Any]]:
    """Fetch comparable multi-country series from Eurostat for Greece in Context."""
    context_key = getattr(indicator_def, "context_series_key", "")
    dataset_code = getattr(indicator_def, "dataset_code", "")
    indicator_id = getattr(indicator_def, "indicator_id", "")
    if not context_key or not dataset_code:
        return []

    url = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset_code}/{context_key}?format=TSV"
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    response = http_get_with_retries(
        url,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
    )

    if response.status_code != 200:
        preview = response.text[:200].strip()
        raise IngestionError(
            f"Eurostat API returned HTTP {response.status_code} ({response.reason}): {preview}"
        )

    return parse_multi_country_tsv(
        response.text,
        indicator_id=indicator_id,
        retrieved_at=retrieved_at,
    )


def fetch_eurostat_series(
    series: Any = DEFAULT_SERIES,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
) -> list[Observation]:
    """Fetch Eurostat series over HTTP with resilient retries, timeout, and error handling."""
    # Support both SeriesConfig and IndicatorDefinition
    url = getattr(series, "api_url", None) or getattr(series, "source_url", "")
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    response = http_get_with_retries(
        url,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
    )

    if response.status_code != 200:
        preview = response.text[:200].strip()
        raise IngestionError(
            f"Eurostat API returned HTTP {response.status_code} ({response.reason}): {preview}"
        )

    return parse_tsv(
        response.text,
        series=series,
        retrieved_at=retrieved_at,
        source_url=url,
    )


def fetch_greek_gdp(timeout: int = 30) -> list[Observation]:
    """Fetch annual Greek GDP in current million euros from Eurostat TSV."""
    return fetch_eurostat_series(DEFAULT_SERIES, timeout=timeout)
