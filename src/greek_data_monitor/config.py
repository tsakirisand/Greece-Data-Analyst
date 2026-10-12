from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("GDM_DATABASE_URL", "sqlite:///./data/monitor.db")
    )
    max_abs_yoy_change_pct: float = field(
        default_factory=lambda: float(os.getenv("GDM_MAX_ABS_YOY_CHANGE_PCT", "30.0"))
    )
    request_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("GDM_REQUEST_TIMEOUT_SECONDS", "30"))
    )
    min_year: int | None = field(
        default_factory=lambda: int(os.getenv("GDM_MIN_YEAR", "1995"))
        if os.getenv("GDM_MIN_YEAR") != "none"
        else None
    )


@dataclass(frozen=True)
class SeriesConfig:
    series_id: str
    dataset: str
    dimensions: dict[str, str]
    unit: str
    description: str
    source_url: str


def build_eurostat_tsv_url(dataset: str, dimensions: dict[str, str]) -> str:
    """Construct Eurostat SDMX 2.1 TSV dissemination URL for filtered series key."""
    # Standard dimension order for Eurostat nama_10 datasets: freq, unit, na_item, geo
    dim_order = ["freq", "unit", "na_item", "geo"]
    key_parts = [dimensions.get(dim, "*") for dim in dim_order]
    key = ".".join(key_parts)
    return f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset}/{key}?format=TSV"


DEFAULT_SERIES = SeriesConfig(
    series_id="eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR",
    dataset="nama_10_gdp",
    dimensions={"freq": "A", "unit": "CP_MEUR", "na_item": "B1GQ", "geo": "EL"},
    unit="CP_MEUR",
    description="Gross Domestic Product at market prices, Greece, annual, current prices (million EUR)",
    source_url=os.getenv(
        "GDM_EUROSTAT_URL",
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.EL?format=TSV",
    ),
)

# Retain backward-compatible references for external callers
EUROSTAT_URL = DEFAULT_SERIES.source_url
SERIES_QUERY = {
    "geo": "EL",
    "na_item": "B1GQ",
    "unit": "CP_MEUR",
    "lang": "en",
}
