from __future__ import annotations

from typing import Any


def format_gdp_value(value: float | None) -> str:
    """Format numeric GDP in million euros for display."""
    if value is None:
        return "— (Missing)"
    return f"€{value:,.1f} M"


def get_flag_descriptions() -> dict[str, str]:
    """Eurostat observation status flags and missing markers documentation."""
    return {
        ":": "Missing / Not available (Eurostat standard missing marker)",
        "p": "Provisional value (subject to upcoming official revisions)",
        "b": "Break in time series (methodological or conceptual update)",
        "e": "Estimated value by official statisticians",
        "u": "Low reliability / high uncertainty",
        "c": "Confidential data",
        "d": "Definition differs",
        "z": "Not applicable",
    }


def get_quality_rule_descriptions() -> dict[str, dict[str, str]]:
    """Plain-language explanations, importance, and review guidelines for all quality rules."""
    return {
        "valid_period": {
            "name": "Calendar Period Validity",
            "default_severity": "ERROR",
            "plain_explanation": "Checks that the time dimension corresponds to a plausible 4-digit calendar year (1900–2100).",
            "why_it_matters": "Malformed period labels prevent chronological indexing and can cause database corruptions or faulty joins.",
            "review_guidance": "Verify whether the upstream API schema altered its time format (e.g., quarterly strings instead of annual years).",
        },
        "unique_period": {
            "name": "Period Uniqueness",
            "default_severity": "ERROR",
            "plain_explanation": "Ensures no annual period appears more than once in the retrieved dataset.",
            "why_it_matters": "Duplicate periods indicate conflicting observations or an ambiguous dimension query.",
            "review_guidance": "Check the query dimensions to ensure a single unique time series is isolated.",
        },
        "not_null": {
            "name": "Active Series Completeness",
            "default_severity": "ERROR",
            "plain_explanation": "Checks that periods within active official coverage (1995 to present) contain valid numeric data.",
            "why_it_matters": "Unexpected missing values in recent years indicate publication delays or incomplete API responses.",
            "review_guidance": "Confirm if Eurostat has delayed the release or if an unexpected data suppression flag is present.",
        },
        "pre_series_coverage": {
            "name": "Pre-Coverage Historical Context",
            "default_severity": "INFO",
            "plain_explanation": "Documents periods prior to 1995 where Eurostat tables return empty missing markers (':').",
            "why_it_matters": "Provides statistical transparency so users know why pre-1995 columns do not contain numbers.",
            "review_guidance": "Expected behavior: Greek ESA 2010 annual GDP in current prices officially begins in 1995.",
        },
        "year_over_year_change": {
            "name": "Year-over-Year Volatility Check",
            "default_severity": "WARN",
            "plain_explanation": "Flags consecutive annual changes exceeding the configured threshold (default ±30%) for human review.",
            "why_it_matters": "Extreme macro swings are rare under normal conditions and warrant verification against known economic events.",
            "review_guidance": "Heuristic review flag only, NOT an assertion of data error. Structural shocks (e.g. 2008 crisis, 2020 pandemic) cause legitimate swings.",
        },
        "data_revision": {
            "name": "Historical Value Revision",
            "default_severity": "WARN",
            "plain_explanation": "Detects when Eurostat alters the numerical value of a previously published historical observation.",
            "why_it_matters": "National statistical institutes routinely revise GDP estimates as annual accounts are finalized.",
            "review_guidance": "Inspect the Eurostat release calendar and notes to identify the methodological or benchmark revision.",
        },
        "status_revision": {
            "name": "Observation Status Flag Change",
            "default_severity": "INFO",
            "plain_explanation": "Tracks when an observation's flag transitions (e.g., provisional 'p' removed upon finalization).",
            "why_it_matters": "Indicates that an estimate has matured from a preliminary calculation into an official finalized record.",
            "review_guidance": "Informational audit trail. Confirms the data lifecycle progression.",
        },
        "all_rules": {
            "name": "All Rules Satisfied",
            "default_severity": "PASS",
            "plain_explanation": "Indicates that all evaluated observations met every configured quality check.",
            "why_it_matters": "Confirms data integrity and readiness for downstream reporting.",
            "review_guidance": "No action required.",
        },
    }


def compare_run_snapshots(
    old_obs: list[dict[str, Any]],
    new_obs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two observation snapshots and compute detailed additions, removals, and revisions."""
    old_by_period = {int(o["period"]): o for o in old_obs}
    new_by_period = {int(o["period"]): o for o in new_obs}

    all_periods = sorted(set(old_by_period.keys()) | set(new_by_period.keys()))

    diffs: list[dict[str, Any]] = []
    unchanged_count = 0
    added_count = 0
    removed_count = 0
    revised_count = 0

    for period in all_periods:
        in_old = period in old_by_period
        in_new = period in new_by_period

        if in_old and in_new:
            o_item = old_by_period[period]
            n_item = new_by_period[period]

            o_val = o_item.get("value")
            n_val = n_item.get("value")
            o_flag = o_item.get("source_status")
            n_flag = n_item.get("source_status")

            val_changed = (o_val is None and n_val is not None) or (o_val is not None and n_val is None) or (
                o_val is not None and n_val is not None and round(o_val, 4) != round(n_val, 4)
            )
            flag_changed = (o_flag or "") != (n_flag or "")

            if val_changed or flag_changed:
                revised_count += 1
                diff_type = "Value Revised" if val_changed else "Status Flag Changed"
                diffs.append(
                    {
                        "period": period,
                        "change_type": diff_type,
                        "old_value": o_val,
                        "new_value": n_val,
                        "old_status": o_flag,
                        "new_status": n_flag,
                        "value_diff": (n_val - o_val) if (n_val is not None and o_val is not None) else None,
                    }
                )
            else:
                unchanged_count += 1

        elif not in_old and in_new:
            added_count += 1
            n_item = new_by_period[period]
            diffs.append(
                {
                    "period": period,
                    "change_type": "New Period Added",
                    "old_value": None,
                    "new_value": n_item.get("value"),
                    "old_status": None,
                    "new_status": n_item.get("source_status"),
                    "value_diff": None,
                }
            )

        elif in_old and not in_new:
            removed_count += 1
            o_item = old_by_period[period]
            diffs.append(
                {
                    "period": period,
                    "change_type": "Period Removed",
                    "old_value": o_item.get("value"),
                    "new_value": None,
                    "old_status": o_item.get("source_status"),
                    "new_status": None,
                    "value_diff": None,
                }
            )

    has_changes = (added_count > 0) or (removed_count > 0) or (revised_count > 0)

    if not has_changes:
        summary_text = "All observations match the previous run exactly. No revisions, additions, or omissions were detected."
    else:
        parts: list[str] = []
        if revised_count > 0:
            parts.append(f"{revised_count} revised observation(s)")
        if added_count > 0:
            parts.append(f"{added_count} newly added period(s)")
        if removed_count > 0:
            parts.append(f"{removed_count} removed period(s)")
        summary_text = f"Detected changes compared to previous run: {', '.join(parts)}."

    return {
        "has_changes": has_changes,
        "summary": summary_text,
        "revised_count": revised_count,
        "added_count": added_count,
        "removed_count": removed_count,
        "unchanged_count": unchanged_count,
        "total_periods": len(all_periods),
        "diffs": sorted(diffs, key=lambda d: d["period"]),
    }


def filter_and_sort_observations(
    observations: list[dict[str, Any]],
    year_range: tuple[int, int] | None = None,
    status_filter: str = "All",
    search_term: str = "",
    sort_by: str = "period",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    """Filter and sort observation dictionaries for explorer display."""
    filtered: list[dict[str, Any]] = []

    for item in observations:
        period = int(item["period"])
        val = item.get("value")
        flag = item.get("source_status") or ""

        # Year range filter
        if year_range is not None:
            min_yr, max_yr = year_range
            if period < min_yr or period > max_yr:
                continue

        # Status filter
        if status_filter == "Numeric only" and val is None:
            continue
        elif status_filter == "Missing values only" and val is not None:
            continue
        elif status_filter == "Provisional only" and flag != "p":
            continue
        elif status_filter == "Flagged only" and not flag:
            continue

        # Search term filter
        if search_term:
            term = search_term.strip().lower()
            text_rep = f"{period} {val} {flag} {item.get('raw_value', '')}".lower()
            if term not in text_rep:
                continue

        filtered.append(dict(item))

    # Sort
    def sort_key(row: dict[str, Any]) -> Any:
        v = row.get(sort_by)
        if v is None:
            return float("-inf") if ascending else float("inf")
        return v

    return sorted(filtered, key=sort_key, reverse=not ascending)
