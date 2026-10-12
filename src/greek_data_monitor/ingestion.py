from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import re
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
    dataset_name = series.dataset if series else "nama_10_gdp"
    default_unit = series.unit if series else "CP_MEUR"
    default_dimensions = dict(series.dimensions) if series else {}
    resolved_source_url = source_url or (series.source_url if series else "")

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


def fetch_eurostat_series(
    series: SeriesConfig = DEFAULT_SERIES,
    timeout: int = 30,
) -> list[Observation]:
    """Fetch Eurostat series over HTTP with timeout and error handling."""
    url = series.source_url
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "GreekPublicDataQualityMonitor/0.1.0"},
        )
    except requests.exceptions.Timeout as exc:
        raise IngestionError(
            f"Timeout ({timeout}s) fetching Eurostat series from {url}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise IngestionError(
            f"Network error fetching Eurostat series from {url}: {exc}"
        ) from exc

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
