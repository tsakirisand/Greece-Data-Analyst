from __future__ import annotations

import pytest

from greek_data_monitor.catalog import (
    ALL_TOPICS,
    CATALOG_BY_ID,
    CATALOG_BY_SERIES_ID,
    INDICATOR_CATALOG,
    TOPIC_LIMITATIONS_DOCUMENTATION,
)


def test_catalog_covers_all_required_topics() -> None:
    topics_in_catalog = {ind.topic for ind in INDICATOR_CATALOG}
    required_topics = {
        "Economy",
        "People & Society",
        "Energy & Environment",
        "Tourism",
        "Housing",
        "Banking & Finance",
    }
    assert required_topics.issubset(topics_in_catalog)
    assert set(ALL_TOPICS) == required_topics


def test_catalog_indicators_integrity() -> None:
    assert len(INDICATOR_CATALOG) >= 15
    for ind in INDICATOR_CATALOG:
        assert ind.indicator_id.strip() != ""
        assert ind.series_id.startswith("eurostat.") or ind.series_id.startswith("ecb.")
        assert ind.name.strip() != ""
        assert ind.unit.strip() != ""
        assert ind.unit_short.strip() != ""
        assert ind.frequency == "Annual"
        assert ind.source_name.strip() != ""
        assert ind.source_url.startswith("http")
        assert ind.api_url.startswith("http")
        assert ind.dataset_code.strip() != ""
        assert ind.series_key.strip() != ""
        assert isinstance(ind.dimensions, dict)
        assert ind.description.strip() != ""
        assert ind.methodology.strip() != ""
        assert ind.limitations.strip() != ""
        assert 1950 <= ind.start_year <= 2025
        assert ind.yoy_threshold > 0


def test_catalog_lookups() -> None:
    assert len(CATALOG_BY_ID) == len(INDICATOR_CATALOG)
    assert len(CATALOG_BY_SERIES_ID) == len(INDICATOR_CATALOG)
    assert "gdp_nominal" in CATALOG_BY_ID
    assert "unemployment_rate" in CATALOG_BY_ID
    assert "house_price_index" in CATALOG_BY_ID
    assert "bond_yield_10y" in CATALOG_BY_ID


def test_topic_limitations_documentation() -> None:
    assert "tourism_receipts" in TOPIC_LIMITATIONS_DOCUMENTATION
    assert "retail_banking_rates" in TOPIC_LIMITATIONS_DOCUMENTATION
    assert "electricity_prices" in TOPIC_LIMITATIONS_DOCUMENTATION
    for key, doc in TOPIC_LIMITATIONS_DOCUMENTATION.items():
        assert "official_authority" in doc
        assert "why_not_direct_api" in doc
        assert "direct_link" in doc


def test_catalog_change_metrics_and_known_gaps() -> None:
    valid_metrics = {"relative_percent", "percentage_points", "disabled"}
    for ind in INDICATOR_CATALOG:
        assert ind.change_metric in valid_metrics, f"{ind.indicator_id} has invalid change_metric: {ind.change_metric}"
        assert isinstance(ind.known_missing_periods, dict)

    # Specific checks for rate indicators
    rate_indicators = [
        "inflation_rate",
        "unemployment_rate",
        "public_debt_pct",
        "poverty_rate",
        "renewable_energy_share",
        "bond_yield_10y",
    ]
    for ind_id in rate_indicators:
        assert CATALOG_BY_ID[ind_id].change_metric == "percentage_points"

    # Specific check for poverty_rate known structural gaps
    poverty = CATALOG_BY_ID["poverty_rate"]
    assert 2002 in poverty.known_missing_periods
    assert "EU-SILC" in poverty.known_missing_periods[2002]

