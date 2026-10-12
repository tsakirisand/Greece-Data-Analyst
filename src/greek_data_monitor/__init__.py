"""Monitor public Greek statistics for quality issues."""

from .config import DEFAULT_SERIES, SeriesConfig, Settings
from .ingestion import (
    IngestionError,
    Observation,
    fetch_eurostat_series,
    fetch_greek_gdp,
    parse_tsv,
)
from .quality import Finding, inspect
from .store import get_latest_observations, get_run_details, list_runs, save_run

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_SERIES",
    "Finding",
    "IngestionError",
    "Observation",
    "SeriesConfig",
    "Settings",
    "fetch_eurostat_series",
    "fetch_greek_gdp",
    "get_latest_observations",
    "get_run_details",
    "inspect",
    "list_runs",
    "parse_tsv",
    "save_run",
]
