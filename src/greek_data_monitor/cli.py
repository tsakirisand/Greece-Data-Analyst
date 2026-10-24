from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .catalog import CATALOG_BY_ID, CATALOG_BY_SERIES_ID, INDICATOR_CATALOG
from .config import DEFAULT_SERIES, Settings
from .dashboard_service import sync_all_indicators
from .ingestion import IngestionError, fetch_eurostat_series
from .quality import Finding, inspect
from .store import get_latest_observations, get_run_details, list_runs, save_run


def format_finding_line(finding: Finding) -> str:
    """Format single finding for readable terminal display."""
    period_str = f" [{finding.period}]" if finding.period is not None else ""
    tag = f"[{finding.severity}]"
    return f"  {tag:<8} {finding.rule}{period_str}: {finding.message}"


def catalog_command(args: argparse.Namespace) -> int:
    """Print the central indicator catalog and documented sources."""
    print("Greece Data Analyst — Multi-Topic Indicator Catalog")
    print(f"Total Configured Indicators: {len(INDICATOR_CATALOG)}")
    print()
    header = f"{'Topic':<22} {'Indicator Name':<38} {'Unit':<20} {'Source'}"
    print(header)
    print("-" * 105)
    for ind in INDICATOR_CATALOG:
        print(
            f"{ind.topic_icon} {ind.topic:<19} {ind.name[:36]:<38} {ind.unit_short:<20} {ind.source_name}"
        )
    print()
    print("Use 'gdm run --all' to ingest and evaluate all catalog indicators.")
    return 0


def run_command(args: argparse.Namespace) -> int:
    """Execute ingestion, quality evaluation, persistence, and report summary."""
    settings = Settings()
    db_url = args.db_url or settings.database_url
    threshold = (
        float(args.threshold)
        if args.threshold is not None
        else settings.max_abs_yoy_change_pct
    )
    timeout = (
        int(args.timeout)
        if args.timeout is not None
        else settings.request_timeout_seconds
    )
    min_year = (
        None
        if args.min_year == "none"
        else (int(args.min_year) if args.min_year is not None else settings.min_year)
    )

    # Check if user requested all indicators
    if getattr(args, "all", False):
        print("Greece Data Analyst — Syncing All Catalog Indicators")
        print(f"Database: {db_url}")
        print(f"Total Indicators: {len(INDICATOR_CATALOG)}")
        print("=" * 70)
        sync_result = sync_all_indicators(db_url, timeout=timeout)
        print()
        print(f"Ingestion Finished: {sync_result['success']} succeeded, {sync_result['failed']} failed")
        print("-" * 70)
        for res in sync_result["details"]:
            status_icon = "✅" if res["status"] == "SUCCESS" else "❌"
            if res["status"] == "SUCCESS":
                print(
                    f"{status_icon} {res['name'][:35]:<36} | Run #{res['run_id']} | "
                    f"Latest: {res['latest_period']} ({res['latest_value']}) | "
                    f"Obs: {res['observation_count']}"
                )
            else:
                print(
                    f"{status_icon} {res['name'][:35]:<36} | FAILED: {res['error_message']}"
                )
        return 0 if sync_result["success"] > 0 else 1

    # Determine series to fetch
    target_series = DEFAULT_SERIES
    series_name = f"Eurostat {DEFAULT_SERIES.dataset}"
    target_start_year = min_year
    target_threshold = threshold

    if getattr(args, "series", None):
        series_arg = args.series.strip()
        matched_ind = CATALOG_BY_ID.get(series_arg) or CATALOG_BY_SERIES_ID.get(series_arg)
        if matched_ind:
            target_series = matched_ind
            series_name = f"{matched_ind.name} ({matched_ind.dataset_code})"
            target_start_year = matched_ind.start_year if min_year is None else min_year
            target_threshold = matched_ind.yoy_threshold if args.threshold is None else threshold
        else:
            print(f"Unknown series or indicator identifier: {series_arg}", file=sys.stderr)
            print("Run 'gdm catalog' to see available identifiers.", file=sys.stderr)
            return 1

    # 1. Fetch data
    series_id = getattr(target_series, "series_id", DEFAULT_SERIES.series_id)
    try:
        observations = fetch_eurostat_series(target_series, timeout=timeout)
    except IngestionError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected ingestion failure: {exc}", file=sys.stderr)
        return 1

    # 2. Look up previous snapshot for revision detection
    previous_observations = []
    try:
        previous_observations = get_latest_observations(db_url, series_id)
    except Exception:
        pass

    # 3. Inspect quality
    target_metric = getattr(target_series, "change_metric", "relative_percent")
    target_missing = getattr(target_series, "known_missing_periods", {})
    findings = inspect(
        observations,
        threshold_pct=target_threshold,
        previous_observations=previous_observations,
        min_year=target_start_year,
        change_metric=target_metric,
        known_missing_periods=target_missing,
    )

    # 4. Persist run and snapshot
    try:
        run_id = save_run(
            database_url=db_url,
            observations=observations,
            findings=findings,
            series_id=series_id,
        )
    except Exception as exc:
        print(f"Database persistence failed: {exc}", file=sys.stderr)
        return 1

    # 5. Output summary
    numeric_count = sum(1 for o in observations if o.value is not None)
    missing_count = len(observations) - numeric_count
    flagged_count = sum(1 for o in observations if o.source_status is not None)
    error_count = sum(1 for f in findings if f.severity == "ERROR")
    warn_count = sum(1 for f in findings if f.severity == "WARN")

    run_status = "FAIL" if error_count > 0 else ("WARN" if warn_count > 0 else "PASS")

    print(f"Greece Data Analyst — Run #{run_id}")
    print(f"Status: {run_status} ({error_count} error(s), {warn_count} warning(s))")
    print(f"Series: {series_name} | series_id={series_id}")
    print(
        f"Observations: {len(observations)} total ({numeric_count} numeric, "
        f"{missing_count} missing, {flagged_count} with status flags)"
    )
    print(f"Database: {db_url}")
    print()
    print("Quality Findings:")
    for finding in findings:
        print(format_finding_line(finding))

    if error_count > 0:
        return 2
    return 0


def history_command(args: argparse.Namespace) -> int:
    """Inspect recent quality runs or detailed findings for a specific run."""
    settings = Settings()
    db_url = args.db_url or settings.database_url

    if args.run_id:
        details = get_run_details(db_url, args.run_id)
        if not details:
            print(f"Run #{args.run_id} not found in database {db_url}", file=sys.stderr)
            return 1

        run = details["run"]
        print(f"Quality Run #{run['id']} Details")
        print(f"Series: {run['series_id']}")
        print(f"Checked at: {run['checked_at']}")
        print(
            f"Status: {run['status']} (Errors: {run['error_count']}, "
            f"Warnings: {run['warning_count']})"
        )
        print(f"Observations: {run['observation_count']}")
        print(f"Source URL: {run['source_url']}")
        print()
        print(f"Findings ({len(details['findings'])}):")
        for f in details["findings"]:
            period_str = f" [{f['period']}]" if f["period"] is not None else ""
            print(f"  [{f['severity']:<5}] {f['rule']}{period_str}: {f['message']}")
        return 0

    runs = list_runs(db_url, limit=args.limit)
    if not runs:
        print(f"No recorded quality runs found in {db_url}")
        print("Run 'greek-data-monitor run' to record the first snapshot.")
        return 0

    print("Greece Data Analyst — Recent Quality Runs")
    print(f"Database: {db_url}")
    print()
    header = f"{'ID':<6} {'Checked At (UTC)':<28} {'Status':<8} {'Obs':<6} {'Errors':<8} {'Warns':<8} {'Series'}"
    print(header)
    print("-" * len(header))
    for r in runs:
        print(
            f"{r['id']:<6} {r['checked_at'][:23]:<28} {r['status']:<8} "
            f"{r['observation_count']:<6} {r['error_count']:<8} {r['warning_count']:<8} "
            f"{r['series_id']}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line interface argument parser."""
    parser = argparse.ArgumentParser(
        prog="greek-data-monitor",
        description="Monitor quality of official public statistics for Greece",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'catalog' subcommand
    subparsers.add_parser(
        "catalog",
        help="List all supported indicators across Economy, Society, Energy, Tourism, Housing, Finance",
    )

    # 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Fetch Eurostat series, run quality checks, and record snapshot",
    )
    run_parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest and run quality checks for all configured catalog indicators",
    )
    run_parser.add_argument(
        "--series",
        dest="series",
        default=None,
        help="Specific indicator ID or series ID to ingest (default: Nominal GDP)",
    )
    run_parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="Database URL (default: $GDM_DATABASE_URL or sqlite:///./data/monitor.db)",
    )
    run_parser.add_argument(
        "--threshold",
        dest="threshold",
        type=float,
        default=None,
        help="Year-over-year percentage change warning threshold (default: series-specific or 30.0)",
    )
    run_parser.add_argument(
        "--min-year",
        dest="min_year",
        default=None,
        help="Minimum expected year for active series (default: series-specific, or 'none')",
    )
    run_parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=None,
        help="HTTP request timeout in seconds (default: 30)",
    )

    # 'history' subcommand
    history_parser = subparsers.add_parser(
        "history",
        aliases=["runs"],
        help="Inspect historical quality runs and findings",
    )
    history_parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="Database URL (default: $GDM_DATABASE_URL or sqlite:///./data/monitor.db)",
    )
    history_parser.add_argument(
        "--limit",
        dest="limit",
        type=int,
        default=10,
        help="Maximum number of runs to display (default: 10)",
    )
    history_parser.add_argument(
        "--run-id",
        dest="run_id",
        type=int,
        default=None,
        help="Specific run ID to inspect in detail",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        exit_code = run_command(args)
    elif args.command in ("history", "runs"):
        exit_code = history_command(args)
    elif args.command == "catalog":
        exit_code = catalog_command(args)
    else:
        parser.print_help()
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
