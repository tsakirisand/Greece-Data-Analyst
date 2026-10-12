from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .config import DEFAULT_SERIES, Settings
from .ingestion import IngestionError, fetch_eurostat_series
from .quality import Finding, inspect
from .store import get_latest_observations, get_run_details, list_runs, save_run


def format_finding_line(finding: Finding) -> str:
    """Format single finding for readable terminal display."""
    period_str = f" [{finding.period}]" if finding.period is not None else ""
    tag = f"[{finding.severity}]"
    return f"  {tag:<8} {finding.rule}{period_str}: {finding.message}"


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

    # 1. Fetch data
    try:
        observations = fetch_eurostat_series(DEFAULT_SERIES, timeout=timeout)
    except IngestionError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected ingestion failure: {exc}", file=sys.stderr)
        return 1

    # 2. Look up previous snapshot for revision detection
    previous_observations = []
    try:
        previous_observations = get_latest_observations(
            db_url, DEFAULT_SERIES.series_id
        )
    except Exception as exc:
        # Non-fatal if database is not yet initialized or empty
        pass

    # 3. Inspect quality
    findings = inspect(
        observations,
        threshold_pct=threshold,
        previous_observations=previous_observations,
        min_year=min_year,
    )

    # 4. Persist run and snapshot
    try:
        run_id = save_run(
            database_url=db_url,
            observations=observations,
            findings=findings,
            series_id=DEFAULT_SERIES.series_id,
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

    print(f"Greek Public Data Quality Monitor — Run #{run_id}")
    print(f"Status: {run_status} ({error_count} error(s), {warn_count} warning(s))")
    print(
        f"Series: Eurostat {DEFAULT_SERIES.dataset} | geo={DEFAULT_SERIES.dimensions.get('geo')} | "
        f"item={DEFAULT_SERIES.dimensions.get('na_item')} | unit={DEFAULT_SERIES.unit}"
    )
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

    print("Greek Public Data Quality Monitor — Recent Quality Runs")
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

    # 'run' subcommand
    run_parser = subparsers.add_parser(
        "run",
        help="Fetch Eurostat series, run quality checks, and record snapshot",
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
        help="Year-over-year percentage change warning threshold (default: 30.0)",
    )
    run_parser.add_argument(
        "--min-year",
        dest="min_year",
        default=None,
        help="Minimum expected year for active series (default: 1995, or 'none')",
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
    else:
        parser.print_help()
        exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
