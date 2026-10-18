from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .ingestion import Observation


@dataclass(frozen=True)
class Finding:
    severity: str  # "ERROR", "WARN", "INFO", "PASS"
    rule: str
    message: str
    period: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


def inspect(
    observations: list[Observation],
    threshold_pct: float = 30.0,
    previous_observations: list[Observation] | None = None,
    min_year: int | None = 1995,
    change_metric: str = "relative_percent",  # "relative_percent", "percentage_points", "disabled"
    known_missing_periods: dict[int, str] | None = None,
) -> list[Finding]:
    """Execute quality rules against a series of observations.

    Rules checked:
    1. valid_period: Periods must be plausible 4-digit calendar years.
    2. unique_period: No period may be duplicated in the series.
    3. not_null / completeness: Active series periods must contain numeric values.
       Documented structural breaks (known_missing_periods) report as INFO rather than ERROR.
    4. year_over_year_change: Large YoY swings flag for review (WARN, not ERROR),
       evaluated in percentage points (pp) for rate series or relative % for level series.
    5. data_revision: Compares against previous run snapshots to detect historical revisions.
    """
    findings: list[Finding] = []

    if not observations:
        return [Finding("ERROR", "empty_series", "No observations provided to inspect")]

    # 1. Period validity check
    for item in observations:
        if item.period < 1900 or item.period > 2100:
            findings.append(
                Finding(
                    severity="ERROR",
                    rule="valid_period",
                    message=f"Period {item.period} is out of expected calendar range (1900-2100)",
                    period=item.period,
                    details={"period": item.period},
                )
            )

    # 2. Duplicate period check
    period_counts = Counter(item.period for item in observations)
    for period, count in sorted(period_counts.items()):
        if count > 1:
            findings.append(
                Finding(
                    severity="ERROR",
                    rule="unique_period",
                    message=f"Period {period} occurs {count} times in the fetched series",
                    period=period,
                    details={"period": period, "occurrences": count},
                )
            )

    # Sort observations by period for ordered checks
    ordered = sorted(observations, key=lambda item: item.period)

    # 3. Completeness / null check
    for item in ordered:
        if item.value is None:
            if min_year is not None and item.period < min_year:
                findings.append(
                    Finding(
                        severity="INFO",
                        rule="pre_series_coverage",
                        message=(
                            f"Missing value for historical period {item.period} "
                            f"prior to official series coverage start ({min_year})"
                        ),
                        period=item.period,
                        details={"period": item.period, "raw_value": item.raw_value},
                    )
                )
            elif known_missing_periods and item.period in known_missing_periods:
                gap_reason = known_missing_periods[item.period]
                findings.append(
                    Finding(
                        severity="INFO",
                        rule="known_structural_gap",
                        message=(
                            f"Documented structural missing period for {item.period}: {gap_reason}"
                        ),
                        period=item.period,
                        details={
                            "period": item.period,
                            "raw_value": item.raw_value,
                            "source_status": item.source_status,
                            "reason": gap_reason,
                        },
                    )
                )
            else:
                findings.append(
                    Finding(
                        severity="ERROR",
                        rule="not_null",
                        message=(
                            f"No numeric value for {item.period} "
                            f"(raw: '{item.raw_value or 'None'}', status: '{item.source_status or 'None'}')"
                        ),
                        period=item.period,
                        details={
                            "period": item.period,
                            "raw_value": item.raw_value,
                            "source_status": item.source_status,
                        },
                    )
                )

    # 4. Year-over-year change check
    numeric_ordered = [item for item in ordered if item.value is not None]
    if change_metric != "disabled":
        for idx in range(1, len(numeric_ordered)):
            prev = numeric_ordered[idx - 1]
            curr = numeric_ordered[idx]

            # Only evaluate consecutive annual periods
            if curr.period == prev.period + 1 and prev.value is not None and curr.value is not None:
                if change_metric == "percentage_points":
                    change_pp = curr.value - prev.value
                    if abs(change_pp) > threshold_pct:
                        findings.append(
                            Finding(
                                severity="WARN",
                                rule="year_over_year_change",
                                message=(
                                    f"{change_pp:+.1f} pp shift from {prev.period} ({prev.value:,.2f}) "
                                    f"to {curr.period} ({curr.value:,.2f}); review source revisions and metadata"
                                ),
                                period=curr.period,
                                details={
                                    "previous_period": prev.period,
                                    "previous_value": prev.value,
                                    "current_period": curr.period,
                                    "current_value": curr.value,
                                    "change_pp": round(change_pp, 2),
                                    "threshold_pp": threshold_pct,
                                    "metric": "percentage_points",
                                },
                            )
                        )
                else:  # relative_percent
                    # Safely handle zero or near-zero previous values
                    if abs(prev.value) < 1e-6:
                        change_abs = curr.value - prev.value
                        if abs(change_abs) > 0.0:
                            findings.append(
                                Finding(
                                    severity="INFO",
                                    rule="year_over_year_change",
                                    message=(
                                        f"Shift from zero baseline at {prev.period} ({prev.value}) "
                                        f"to {curr.period} ({curr.value:,.2f}); relative change undefined"
                                    ),
                                    period=curr.period,
                                    details={
                                        "previous_period": prev.period,
                                        "previous_value": prev.value,
                                        "current_period": curr.period,
                                        "current_value": curr.value,
                                        "change_abs": round(change_abs, 2),
                                        "metric": "relative_percent",
                                    },
                                )
                            )
                    else:
                        change = (curr.value - prev.value) / abs(prev.value) * 100.0
                        if abs(change) > threshold_pct:
                            findings.append(
                                Finding(
                                    severity="WARN",
                                    rule="year_over_year_change",
                                    message=(
                                        f"{change:+.1f}% change from {prev.period} ({prev.value:,.1f}) "
                                        f"to {curr.period} ({curr.value:,.1f}); review source revisions and metadata"
                                    ),
                                    period=curr.period,
                                    details={
                                        "previous_period": prev.period,
                                        "previous_value": prev.value,
                                        "current_period": curr.period,
                                        "current_value": curr.value,
                                        "change_pct": round(change, 2),
                                        "threshold_pct": threshold_pct,
                                        "metric": "relative_percent",
                                    },
                                )
                            )

    # 5. Historical revision check (against previous snapshot if available)
    if previous_observations:
        prev_map = {item.period: item for item in previous_observations}
        for curr in ordered:
            if curr.period in prev_map:
                prev = prev_map[curr.period]
                if prev.value != curr.value:
                    findings.append(
                        Finding(
                            severity="WARN",
                            rule="data_revision",
                            message=(
                                f"Historical observation for {curr.period} revised: "
                                f"previously {prev.value} (flag: '{prev.source_status}'), "
                                f"now {curr.value} (flag: '{curr.source_status}')"
                            ),
                            period=curr.period,
                            details={
                                "period": curr.period,
                                "previous_value": prev.value,
                                "current_value": curr.value,
                                "previous_status": prev.source_status,
                                "current_status": curr.source_status,
                            },
                        )
                    )
                elif prev.source_status != curr.source_status:
                    findings.append(
                        Finding(
                            severity="INFO",
                            rule="status_revision",
                            message=(
                                f"Status flag for {curr.period} changed from "
                                f"'{prev.source_status}' to '{curr.source_status}'"
                            ),
                            period=curr.period,
                            details={
                                "period": curr.period,
                                "previous_status": prev.source_status,
                                "current_status": curr.source_status,
                            },
                        )
                    )

    if not any(f.severity in ("ERROR", "WARN") for f in findings):
        findings.append(
            Finding(
                severity="PASS",
                rule="all_rules",
                message=f"{len(observations)} observations passed configured quality checks",
            )
        )

    return findings
