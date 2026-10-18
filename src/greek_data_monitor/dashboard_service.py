from __future__ import annotations

from typing import Any


def format_gdp_value(value: float | None) -> str:
    """Format numeric GDP in million euros for display."""
    if value is None:
        return "— (Missing)"
    return f"€{value:,.1f} M"


def format_indicator_value(
    value: float | None,
    unit: str = "",
    unit_short: str = "",
) -> str:
    """Format any numeric indicator value appropriately based on its unit and magnitude."""
    if value is None:
        return "— (Missing)"

    u_lower = (unit + " " + unit_short).lower()
    if "meur" in u_lower or "million" in u_lower or "€m" in u_lower:
        return f"€{value:,.1f} M"
    elif "%" in u_lower or "pc" in u_lower or "rate" in u_lower or "yield" in u_lower:
        return f"{value:.2f}%"
    elif "year" in u_lower or "yr" in u_lower:
        return f"{value:.1f} yrs"
    elif "pers" in u_lower or "nr" in u_lower or "night" in u_lower or "arrival" in u_lower:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.2f} M"
        elif abs(value) >= 1_000:
            return f"{value:,.0f}"
        return f"{value:.0f}"
    elif "mtoe" in u_lower:
        return f"{value:.2f} MTOE"
    elif "co2" in u_lower or "ths_t" in u_lower or "kt" in u_lower:
        return f"{value:,.1f} kt"
    elif "idx" in u_lower or "index" in u_lower:
        return f"{value:.2f}"
    else:
        return f"{value:,.2f}"


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
        "known_structural_gap": {
            "name": "Documented Structural Survey Gap",
            "default_severity": "INFO",
            "plain_explanation": "Documents known, officially published survey transitions or methodology breaks (e.g. EU-SILC 2002 transition).",
            "why_it_matters": "Distinguishes officially documented statistical breaks from pipeline ingestion errors.",
            "review_guidance": "Expected official behavior documented by Eurostat and national institutes.",
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


def calculate_quality_scorecard(
    observations: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    min_year: int = 1995,
    known_missing_periods: dict[int, str] | list[int] | set[int] | None = None,
) -> dict[str, Any]:
    """Calculate ISO 25012 / DAMA data quality dimension scores and composite grade."""
    total_obs = len(observations)
    if total_obs == 0:
        return {
            "overall_score": 0.0,
            "grade": "F",
            "completeness_score": 0.0,
            "validity_score": 0.0,
            "uniqueness_score": 0.0,
            "plausibility_score": 0.0,
            "error_count": 0,
            "warning_count": 0,
        }

    # 1. Completeness: active series coverage (>= min_year) excluding documented structural gaps
    known_gaps = (
        set(known_missing_periods.keys())
        if isinstance(known_missing_periods, dict)
        else set(known_missing_periods or [])
    )
    active_obs = [
        o for o in observations
        if int(o["period"]) >= min_year and int(o["period"]) not in known_gaps
    ]
    if active_obs:
        numeric_active = sum(1 for o in active_obs if o.get("value") is not None)
        completeness = round((numeric_active / len(active_obs)) * 100.0, 1)
    else:
        completeness = 100.0

    # 2. Validity & Uniqueness penalties based on error findings
    invalid_periods = sum(1 for f in findings if f.get("rule") == "valid_period")
    validity = max(0.0, 100.0 - (invalid_periods * 30.0))

    duplicate_periods = sum(1 for f in findings if f.get("rule") == "unique_period")
    uniqueness = max(0.0, 100.0 - (duplicate_periods * 30.0))

    # 3. Plausibility / Volatility stability
    warn_count = sum(1 for f in findings if f.get("severity") == "WARN")
    plausibility = max(0.0, 100.0 - (warn_count * 15.0))

    err_count = sum(1 for f in findings if f.get("severity") == "ERROR")

    # Composite Score
    composite = round(
        (0.35 * completeness) + (0.25 * validity) + (0.25 * uniqueness) + (0.15 * plausibility),
        1,
    )
    if err_count > 0:
        composite = min(composite, 65.0)  # Cap if critical errors exist

    if composite >= 95.0:
        grade = "A+"
    elif composite >= 90.0:
        grade = "A"
    elif composite >= 80.0:
        grade = "B"
    elif composite >= 70.0:
        grade = "C"
    else:
        grade = "F"

    return {
        "overall_score": composite,
        "grade": grade,
        "completeness_score": completeness,
        "validity_score": validity,
        "uniqueness_score": uniqueness,
        "plausibility_score": plausibility,
        "error_count": err_count,
        "warning_count": warn_count,
        "active_period_count": len(active_obs),
    }


def get_greek_economic_milestones() -> list[dict[str, Any]]:
    """Key macroeconomic and historical milestones for overlaying on Greece's GDP curve."""
    return [
        {"year": 2001, "label": "Eurozone Entry", "color": "#10b981", "desc": "Greece formally joins the European Economic and Monetary Union."},
        {"year": 2009, "label": "Debt Crisis Onset", "color": "#ef4444", "desc": "Deficit revisions trigger sovereign debt crisis."},
        {"year": 2012, "label": "PSI Debt Restructuring", "color": "#f59e0b", "desc": "Private sector bond haircut and major restructuring."},
        {"year": 2015, "label": "Capital Controls", "color": "#f97316", "desc": "Referendum, capital restrictions, and third economic program."},
        {"year": 2020, "label": "COVID-19 Shock", "color": "#dc2626", "desc": "Global pandemic lockdowns contraction."},
        {"year": 2023, "label": "Investment Grade", "color": "#06b6d4", "desc": "Credit rating agencies restore Greece to investment grade."},
    ]


def calculate_statistical_anomalies(
    df_numeric: Any,  # pd.DataFrame
    z_threshold: float = 1.75,
) -> dict[str, Any]:
    """Compute rolling growth metrics, standard deviations, and Z-score anomalies."""
    if df_numeric is None or len(df_numeric) < 3 or "yoy_change_pct" not in df_numeric.columns:
        return {"mean_growth": 0.0, "std_growth": 0.0, "anomalies": []}

    valid_changes = df_numeric["yoy_change_pct"].dropna()
    mean_val = float(valid_changes.mean())
    std_val = float(valid_changes.std()) if len(valid_changes) > 1 else 1.0

    anomalies: list[dict[str, Any]] = []
    for _, row in df_numeric.dropna(subset=["yoy_change_pct"]).iterrows():
        yoy = float(row["yoy_change_pct"])
        z_score = (yoy - mean_val) / std_val if std_val > 0 else 0.0
        if abs(z_score) >= z_threshold:
            anomalies.append(
                {
                    "period": int(row["period"]),
                    "value": float(row["value"]),
                    "yoy_change_pct": round(yoy, 2),
                    "z_score": round(z_score, 2),
                    "direction": "Surge" if z_score > 0 else "Contraction",
                }
            )

    return {
        "mean_growth": round(mean_val, 2),
        "std_growth": round(std_val, 2),
        "anomalies": sorted(anomalies, key=lambda a: a["period"]),
    }


def generate_markdown_audit_report(
    run_dict: dict[str, Any],
    findings: list[dict[str, Any]],
    scorecard: dict[str, Any],
    series_name: str,
) -> str:
    """Generate a downloadable executive data quality audit report in Markdown format."""
    run_id = run_dict.get("id", "N/A")
    checked_at = run_dict.get("checked_at", "")[:19].replace("T", " ")
    status = run_dict.get("status", "PASS")
    obs_count = run_dict.get("observation_count", 0)

    report = f"""# Official Data Quality Audit Report: Greece Public Statistics

**Series:** {series_name}
**Audit Run ID:** #{run_id}
**Audit Timestamp:** {checked_at} UTC
**Overall Surveillance Status:** {status}
**Data Quality Score:** {scorecard.get('overall_score', 0)}/100 (Grade: {scorecard.get('grade', 'N/A')})

---

## 1. Executive Summary
This audit report was automatically compiled by the Greek Public Data Quality Monitor. The monitored indicator has been evaluated against ISO 25012 and DAMA statistical quality dimensions.

- **Total Observations Analyzed:** {obs_count}
- **Active Coverage Periods (≥ 1995):** {scorecard.get('active_period_count', 0)}
- **Errors Detected:** {scorecard.get('error_count', 0)}
- **Review Warnings:** {scorecard.get('warning_count', 0)}

---

## 2. Data Quality Dimensions Scorecard
| Quality Dimension | Score | Assessment |
|---|---|---|
| **Completeness** | {scorecard.get('completeness_score', 0)}% | Active series periods containing valid numeric observations |
| **Period Validity** | {scorecard.get('validity_score', 0)}% | Calendar year conformity (1900–2100) |
| **Uniqueness** | {scorecard.get('uniqueness_score', 0)}% | Absence of duplicate temporal observations |
| **Plausibility & Volatility** | {scorecard.get('plausibility_score', 0)}% | Stability within expected annual growth bounds |

---

## 3. Findings Audit Log
| Severity | Rule | Period | Finding Description |
|---|---|---|---|
"""
    for f in findings:
        p_str = str(f.get("period")) if f.get("period") is not None else "All"
        report += f"| {f.get('severity')} | `{f.get('rule')}` | {p_str} | {f.get('message')} |\n"

    report += """
---

## 4. Methodology & Disclaimer
- **Data Source:** Eurostat Dissemination API (`nama_10_gdp`).
- **Heuristic Boundaries:** Percentage changes are review heuristics, not proof that official statistics are inaccurate. Macroeconomic shocks and statistical revisions legitimately alter historical series.
- **Licensing:** Free reuse subject to Eurostat open data reuse policy.
"""
    return report


def sync_all_indicators(
    database_url: str,
    indicators: list[Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Ingest all configured catalog indicators independently.

    An error for one indicator must not hide other stored indicators.
    """
    from .catalog import INDICATOR_CATALOG
    from .ingestion import fetch_eurostat_series, fetch_indicator_benchmarks
    from .quality import inspect
    from .store import get_latest_observations, save_country_benchmarks, save_run

    target_indicators = indicators or INDICATOR_CATALOG
    results: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    for ind in target_indicators:
        ind_id = getattr(ind, "indicator_id", "")
        series_id = getattr(ind, "series_id", "")
        name = getattr(ind, "name", ind_id)
        start_year = getattr(ind, "start_year", 1995)
        threshold = getattr(ind, "yoy_threshold", 30.0)
        change_metric = getattr(ind, "change_metric", "relative_percent")
        known_missing = getattr(ind, "known_missing_periods", {})

        try:
            previous_obs = get_latest_observations(database_url, series_id)
            fetched_obs = fetch_eurostat_series(ind, timeout=timeout)
            findings = inspect(
                fetched_obs,
                threshold_pct=threshold,
                previous_observations=previous_obs,
                min_year=start_year,
                change_metric=change_metric,
                known_missing_periods=known_missing,
            )
            run_id = save_run(
                database_url=database_url,
                observations=fetched_obs,
                findings=findings,
                series_id=series_id,
            )

            # Ingest multi-country benchmark if applicable
            benchmarks_count = 0
            if getattr(ind, "comparable_eu", False) and getattr(ind, "context_series_key", ""):
                try:
                    benchmarks = fetch_indicator_benchmarks(ind, timeout=timeout)
                    if benchmarks:
                        benchmarks_count = save_country_benchmarks(
                            database_url, ind_id, benchmarks
                        )
                except Exception:
                    pass

            numeric_obs = [o for o in fetched_obs if o.value is not None]
            latest_obs = numeric_obs[-1] if numeric_obs else None

            results.append(
                {
                    "indicator_id": ind_id,
                    "series_id": series_id,
                    "name": name,
                    "status": "SUCCESS",
                    "run_id": run_id,
                    "observation_count": len(fetched_obs),
                    "latest_period": latest_obs.period if latest_obs else None,
                    "latest_value": latest_obs.value if latest_obs else None,
                    "benchmarks_count": benchmarks_count,
                    "error_message": None,
                }
            )
            success_count += 1
        except Exception as exc:
            results.append(
                {
                    "indicator_id": ind_id,
                    "series_id": series_id,
                    "name": name,
                    "status": "ERROR",
                    "run_id": None,
                    "observation_count": 0,
                    "latest_period": None,
                    "latest_value": None,
                    "benchmarks_count": 0,
                    "error_message": str(exc),
                }
            )
            fail_count += 1

    return {
        "total": len(target_indicators),
        "success": success_count,
        "failed": fail_count,
        "details": results,
    }


def get_overview_kpis(database_url: str, headline_only: bool = False) -> list[dict[str, Any]]:
    """Retrieve the latest observations and summary statistics for indicators across topics.

    If headline_only is True, filters to primary headline metrics.
    Otherwise returns all indicators in the catalog.
    """
    from .catalog import INDICATOR_CATALOG
    from .store import get_latest_observations

    kpis: list[dict[str, Any]] = []

    # Headline indicators representing each core topic
    headline_ids = {
        "gdp_nominal",
        "unemployment_rate",
        "inflation_rate",
        "public_debt_pct",
        "population",
        "renewable_energy_share",
        "house_price_index",
        "tourist_arrivals",
        "bond_yield_10y",
    }

    for ind in INDICATOR_CATALOG:
        is_headline = ind.indicator_id in headline_ids
        if headline_only and not is_headline:
            continue

        obs = get_latest_observations(database_url, ind.series_id)
        valid_obs = [o for o in obs if o.value is not None]

        latest = valid_obs[-1] if valid_obs else None
        prev = valid_obs[-2] if len(valid_obs) >= 2 else None

        yoy_pct: float | None = None
        yoy_abs: float | None = None
        if latest and prev and prev.value is not None and prev.value != 0:
            yoy_abs = latest.value - prev.value
            yoy_pct = (yoy_abs / abs(prev.value)) * 100.0

        formatted_val = format_indicator_value(
            latest.value if latest else None,
            unit=ind.unit,
            unit_short=ind.unit_short,
        )

        kpis.append(
            {
                "indicator_id": ind.indicator_id,
                "series_id": ind.series_id,
                "name": ind.name,
                "topic": ind.topic,
                "topic_icon": ind.topic_icon,
                "unit": ind.unit,
                "unit_short": ind.unit_short,
                "is_headline": is_headline,
                "latest_period": latest.period if latest else None,
                "latest_value": latest.value if latest else None,
                "formatted_value": formatted_val,
                "source_status": latest.source_status if latest else None,
                "prev_period": prev.period if prev else None,
                "prev_value": prev.value if prev else None,
                "yoy_change_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
                "yoy_change_abs": round(yoy_abs, 2) if yoy_abs is not None else None,
                "source_name": ind.source_name,
                "retrieved_at": latest.retrieved_at if latest else None,
                "has_data": latest is not None,
                "observation_count": len(valid_obs),
            }
        )

    return kpis


def get_what_changed_summary(database_url: str) -> list[dict[str, Any]]:
    """Synthesize a plain-language summary of important changes since the previous period."""
    kpis = get_overview_kpis(database_url, headline_only=False)
    changes: list[dict[str, Any]] = []

    for k in kpis:
        if not k["has_data"] or k["yoy_change_pct"] is None:
            continue

        pct = k["yoy_change_pct"]
        period = k["latest_period"]
        prev_p = k["prev_period"]
        name = k["name"]
        icon = k["topic_icon"]
        val_str = k["formatted_value"]

        # Plain language assessment
        if abs(pct) >= 15.0:
            impact = "High Shift"
            badge = "WARN"
        elif abs(pct) >= 5.0:
            impact = "Moderate Move"
            badge = "INFO"
        else:
            impact = "Stable Trend"
            badge = "PASS"

        direction = "increased" if pct > 0 else "decreased"
        sign = "+" if pct > 0 else ""

        narrative = (
            f"{name} reached {val_str} in {period}, having {direction} by {sign}{pct:.1f}% "
            f"compared to {prev_p}."
        )

        changes.append(
            {
                "topic": k["topic"],
                "topic_icon": icon,
                "indicator": name,
                "period": period,
                "change_pct": pct,
                "impact": impact,
                "badge": badge,
                "narrative": narrative,
            }
        )

    return sorted(changes, key=lambda c: abs(c["change_pct"]), reverse=True)


def calculate_indicator_correlation_matrix(
    database_url: str,
    indicator_ids: list[str] | None = None,
    min_periods: int = 5,
) -> dict[str, Any]:
    """Calculate the pairwise Pearson correlation matrix across time-series indicators."""
    from .catalog import INDICATOR_CATALOG
    from .store import get_latest_observations

    selected_catalog = [
        ind for ind in INDICATOR_CATALOG
        if indicator_ids is None or ind.indicator_id in indicator_ids
    ]

    series_map: dict[str, dict[int, float]] = {}
    label_map: dict[str, str] = {}

    for ind in selected_catalog:
        obs = get_latest_observations(database_url, ind.series_id)
        valid = {int(o.period): float(o.value) for o in obs if o.value is not None}
        if len(valid) >= min_periods:
            series_map[ind.indicator_id] = valid
            label_map[ind.indicator_id] = f"{ind.topic_icon} {ind.name}"

    if len(series_map) < 2:
        return {
            "indicators": list(series_map.keys()),
            "labels": [label_map[k] for k in series_map],
            "correlation_matrix": [],
            "common_periods_count": 0,
        }

    # Build overlapping dataframe
    import pandas as pd
    df = pd.DataFrame(series_map).dropna()
    if len(df) < min_periods:
        # Fall back to pairwise correlation with min_periods
        df_all = pd.DataFrame(series_map)
        corr_df = df_all.corr(method="pearson", min_periods=min_periods).round(3)
    else:
        corr_df = df.corr(method="pearson").round(3)

    return {
        "indicators": list(corr_df.columns),
        "labels": [label_map.get(col, col) for col in corr_df.columns],
        "correlation_matrix": corr_df.fillna(0.0).values.tolist(),
        "common_periods_count": len(df),
    }


def calculate_safe_comparison(
    obs_a: list[dict[str, Any]],
    meta_a: dict[str, Any],
    obs_b: list[dict[str, Any]],
    meta_b: dict[str, Any],
    base_year: int | None = None,
) -> dict[str, Any]:
    """Ensure indicators are compared safely without distorting raw unit scales.

    If units are identical, comparison proceeds on raw scale.
    If units differ, series are indexed (Base Year = 100) to compare growth dynamics.
    Detects zero, near-zero (<1e-6), missing, or non-finite base values before calculating an indexed series.
    Returns clear structured findings and disables indexing without silently changing the base period.
    """
    import math

    unit_a = meta_a.get("unit_short", meta_a.get("unit", ""))
    unit_b = meta_b.get("unit_short", meta_b.get("unit", ""))
    name_a = meta_a.get("name", "Series A")
    name_b = meta_b.get("name", "Series B")

    dict_a = {int(o["period"]): o.get("value") for o in obs_a if "period" in o}
    dict_b = {int(o["period"]): o.get("value") for o in obs_b if "period" in o}

    common_periods = sorted(set(dict_a.keys()) & set(dict_b.keys()))
    if not common_periods:
        return {
            "compatible_raw": False,
            "requires_indexing": True,
            "indexing_disabled": True,
            "error_explanation": "No overlapping time periods found between the selected indicators.",
            "common_periods": [],
            "data": [],
            "message": "No overlapping time periods found between the selected indicators.",
        }

    compatible_raw = (unit_a == unit_b) and bool(unit_a)
    base_period = base_year if base_year is not None else common_periods[0]

    base_val_a = dict_a.get(base_period)
    base_val_b = dict_b.get(base_period)

    def _check_invalid_base(val: Any) -> str | None:
        if val is None:
            return "missing (null)"
        try:
            f = float(val)
            if math.isnan(f):
                return "non-finite (NaN)"
            if math.isinf(f):
                return "non-finite (Inf)"
            if abs(f) < 1e-6:
                if abs(f) == 0.0:
                    return "zero (0.0)"
                return f"near-zero ({f:.2e})"
            return None
        except (ValueError, TypeError):
            return "non-numeric"

    inv_a = _check_invalid_base(base_val_a)
    inv_b = _check_invalid_base(base_val_b)
    base_in_common = base_period in common_periods

    indexing_possible = (not inv_a) and (not inv_b) and base_in_common

    comparison_data: list[dict[str, Any]] = []
    for p in common_periods:
        val_a = dict_a[p]
        val_b = dict_b[p]

        idx_a: float | None = None
        idx_b: float | None = None
        if indexing_possible and base_val_a is not None and base_val_b is not None:
            if val_a is not None:
                try:
                    idx_a = round((float(val_a) / float(base_val_a)) * 100.0, 2)
                except (ZeroDivisionError, ValueError):
                    idx_a = None
            if val_b is not None:
                try:
                    idx_b = round((float(val_b) / float(base_val_b)) * 100.0, 2)
                except (ZeroDivisionError, ValueError):
                    idx_b = None

        comparison_data.append(
            {
                "period": p,
                "raw_a": val_a,
                "raw_b": val_b,
                "index_a": idx_a,
                "index_b": idx_b,
            }
        )

    if compatible_raw:
        return {
            "compatible_raw": True,
            "requires_indexing": False,
            "indexing_disabled": False,
            "error_explanation": None,
            "unit_a": unit_a,
            "unit_b": unit_b,
            "name_a": name_a,
            "name_b": name_b,
            "base_period": base_period,
            "common_periods": common_periods,
            "data": comparison_data,
            "message": "Matching units allow direct raw-value comparison.",
        }

    if not indexing_possible:
        reasons: list[str] = []
        if not base_in_common:
            reasons.append(f"base year {base_period} is not available in both series")
        if inv_a:
            reasons.append(f"base period {base_period} value for '{name_a}' is {inv_a}")
        if inv_b:
            reasons.append(f"base period {base_period} value for '{name_b}' is {inv_b}")
        reason_msg = "; ".join(reasons)

        return {
            "compatible_raw": False,
            "requires_indexing": True,
            "indexing_disabled": True,
            "error_explanation": reason_msg,
            "unit_a": unit_a,
            "unit_b": unit_b,
            "name_a": name_a,
            "name_b": name_b,
            "base_period": base_period,
            "common_periods": common_periods,
            "data": comparison_data,
            "message": (
                f"Different units ({unit_a} vs {unit_b}) require re-indexing, but base period {base_period} "
                f"cannot be used as a 100 baseline: {reason_msg}. "
                "Indexed comparison is disabled to avoid mathematical distortion or division by zero without silently altering the base period."
            ),
        }

    return {
        "compatible_raw": False,
        "requires_indexing": True,
        "indexing_disabled": False,
        "error_explanation": None,
        "unit_a": unit_a,
        "unit_b": unit_b,
        "name_a": name_a,
        "name_b": name_b,
        "base_period": base_period,
        "common_periods": common_periods,
        "data": comparison_data,
        "message": f"Different units ({unit_a} vs {unit_b}). Both series have been re-indexed (Base {base_period} = 100) to safely compare relative trajectories.",
    }
