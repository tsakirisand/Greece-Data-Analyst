from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from .ingestion import Observation
from .quality import Finding


def _parse_db_target(database_url: str) -> str | Path:
    """Resolve database URL into sqlite3 connectable target."""
    url = database_url.strip()
    if url in (":memory:", "sqlite:///:memory:", "sqlite://:memory:"):
        return ":memory:"
    if url.startswith("sqlite://"):
        raw_path = url.removeprefix("sqlite://")
        # Handle sqlite:///./relative/path -> ./relative/path
        if raw_path.startswith("/./") or raw_path.startswith("/../"):
            return Path(raw_path[1:])
        # Handle sqlite:////absolute/path -> /absolute/path
        if raw_path.startswith("//"):
            return Path(raw_path[1:])
        # Handle sqlite:///absolute/path where absolute path follows
        return Path(raw_path)
    return Path(url)


def get_connection(database_url: str) -> sqlite3.Connection:
    """Establish SQLite connection with foreign keys and row factory enabled."""
    target = _parse_db_target(database_url)
    if isinstance(target, Path):
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target))
    else:
        conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(connection: sqlite3.Connection | str) -> None:
    """Create schema tables and indices if not already present."""
    if isinstance(connection, str):
        with get_connection(connection) as conn:
            init_db(conn)
            return

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS series_metadata (
            series_id TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            unit TEXT NOT NULL,
            source_url TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quality_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            observation_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            error_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            source_url TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES quality_runs(id) ON DELETE CASCADE,
            series_id TEXT NOT NULL,
            period INTEGER NOT NULL,
            value REAL,
            source_status TEXT,
            raw_value TEXT,
            fetched_at TEXT NOT NULL,
            UNIQUE (run_id, period)
        );

        CREATE TABLE IF NOT EXISTS quality_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES quality_runs(id) ON DELETE CASCADE,
            severity TEXT NOT NULL,
            rule TEXT NOT NULL,
            message TEXT NOT NULL,
            period INTEGER,
            details_json TEXT
        );

        CREATE TABLE IF NOT EXISTS country_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id TEXT NOT NULL,
            country_code TEXT NOT NULL,
            country_name TEXT NOT NULL,
            period INTEGER NOT NULL,
            value REAL,
            source_status TEXT,
            fetched_at TEXT NOT NULL,
            UNIQUE (indicator_id, country_code, period)
        );

        CREATE INDEX IF NOT EXISTS idx_observations_series_period
            ON observations(series_id, period);
        CREATE INDEX IF NOT EXISTS idx_quality_runs_series
            ON quality_runs(series_id, checked_at);
        CREATE INDEX IF NOT EXISTS idx_quality_findings_run
            ON quality_findings(run_id);
        CREATE INDEX IF NOT EXISTS idx_country_benchmarks_ind_period
            ON country_benchmarks(indicator_id, period);
        """
    )


def save_run(
    database_url: str,
    observations: list[Observation],
    findings: list[Finding],
    series_id: str = "eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR",
) -> int:
    """Persist a quality run, observations snapshot, findings, and metadata."""
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    error_count = sum(1 for item in findings if item.severity == "ERROR")
    warning_count = sum(1 for item in findings if item.severity == "WARN")
    status = "FAIL" if error_count > 0 else ("WARN" if warning_count > 0 else "PASS")

    # Extract series metadata from observations if available
    first_obs = observations[0] if observations else None
    dataset = first_obs.dataset if first_obs else "nama_10_gdp"
    dimensions = first_obs.dimensions if first_obs else {}
    unit = first_obs.unit if first_obs else "CP_MEUR"
    source_url = first_obs.source_url if first_obs else ""

    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)

            # Upsert series metadata
            conn.execute(
                """
                INSERT INTO series_metadata (series_id, dataset, dimensions_json, unit, source_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(series_id) DO UPDATE SET
                    dataset = excluded.dataset,
                    dimensions_json = excluded.dimensions_json,
                    unit = excluded.unit,
                    source_url = excluded.source_url,
                    updated_at = excluded.updated_at
                """,
                (
                    series_id,
                    dataset,
                    json.dumps(dimensions),
                    unit,
                    source_url,
                    checked_at,
                ),
            )

            # Record quality run
            cursor = conn.execute(
                """
                INSERT INTO quality_runs (series_id, checked_at, observation_count, status, error_count, warning_count, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    series_id,
                    checked_at,
                    len(observations),
                    status,
                    error_count,
                    warning_count,
                    source_url,
                ),
            )
            run_id = int(cursor.lastrowid)

            # Record observations snapshot
            obs_rows = [
                (
                    run_id,
                    series_id,
                    item.period,
                    item.value,
                    item.source_status,
                    item.raw_value,
                    item.retrieved_at or checked_at,
                )
                for item in observations
            ]
            conn.executemany(
                """
                INSERT INTO observations (run_id, series_id, period, value, source_status, raw_value, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                obs_rows,
            )

            # Record quality findings
            finding_rows = [
                (
                    run_id,
                    item.severity,
                    item.rule,
                    item.message,
                    item.period,
                    json.dumps(item.details) if item.details else None,
                )
                for item in findings
            ]
            conn.executemany(
                """
                INSERT INTO quality_findings (run_id, severity, rule, message, period, details_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                finding_rows,
            )

            return run_id
    finally:
        conn.close()


def get_latest_observations(
    database_url: str,
    series_id: str = "eurostat.nama_10_gdp.EL.B1GQ.CP_MEUR",
) -> list[Observation]:
    """Retrieve observations snapshot from the latest recorded run."""
    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            row = conn.execute(
                """
                SELECT id FROM quality_runs
                WHERE series_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (series_id,),
            ).fetchone()

            if not row:
                return []

            latest_run_id = row["id"]

            meta_row = conn.execute(
                "SELECT dataset, dimensions_json, unit, source_url FROM series_metadata WHERE series_id = ?",
                (series_id,),
            ).fetchone()

            dataset = meta_row["dataset"] if meta_row else "nama_10_gdp"
            dims = json.loads(meta_row["dimensions_json"]) if meta_row else {}
            unit = meta_row["unit"] if meta_row else "CP_MEUR"
            src_url = meta_row["source_url"] if meta_row else ""

            obs_rows = conn.execute(
                """
                SELECT period, value, source_status, raw_value, fetched_at
                FROM observations
                WHERE run_id = ?
                ORDER BY period ASC
                """,
                (latest_run_id,),
            ).fetchall()

            return [
                Observation(
                    period=r["period"],
                    value=r["value"],
                    source_status=r["source_status"],
                    dataset=dataset,
                    dimensions=dims,
                    unit=unit,
                    retrieved_at=r["fetched_at"],
                    source_url=src_url,
                    raw_value=r["raw_value"] or "",
                )
                for r in obs_rows
            ]
    finally:
        conn.close()


def list_runs(
    database_url: str,
    limit: int = 10,
    series_id: str | None = None,
) -> list[dict[str, Any]]:
    """List recent quality runs with summary metrics."""
    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            if series_id:
                rows = conn.execute(
                    """
                    SELECT id, series_id, checked_at, observation_count, status, error_count, warning_count, source_url
                    FROM quality_runs
                    WHERE series_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (series_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, series_id, checked_at, observation_count, status, error_count, warning_count, source_url
                    FROM quality_runs
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

            return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run_details(database_url: str, run_id: int) -> dict[str, Any] | None:
    """Retrieve full details for a quality run including findings and observations."""
    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            run_row = conn.execute(
                "SELECT * FROM quality_runs WHERE id = ?",
                (run_id,),
            ).fetchone()

            if not run_row:
                return None

            findings_rows = conn.execute(
                "SELECT id, severity, rule, message, period, details_json FROM quality_findings WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()

            obs_rows = conn.execute(
                "SELECT period, value, source_status, raw_value, fetched_at FROM observations WHERE run_id = ? ORDER BY period ASC",
                (run_id,),
            ).fetchall()

            return {
                "run": dict(run_row),
                "findings": [
                    {
                        "id": f["id"],
                        "severity": f["severity"],
                        "rule": f["rule"],
                        "message": f["message"],
                        "period": f["period"],
                        "details": json.loads(f["details_json"]) if f["details_json"] else {},
                    }
                    for f in findings_rows
                ],
                "observations": [dict(o) for o in obs_rows],
            }
    finally:
        conn.close()


def save_country_benchmarks(
    database_url: str,
    indicator_id: str,
    benchmarks: list[dict[str, Any]],
) -> int:
    """Persist or update multi-country comparative benchmark observations."""
    if not benchmarks:
        return 0

    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            rows = [
                (
                    indicator_id,
                    b["country_code"],
                    b.get("country_name", b["country_code"]),
                    int(b["period"]),
                    b.get("value"),
                    b.get("source_status"),
                    b.get("fetched_at", datetime.now(timezone.utc).isoformat()),
                )
                for b in benchmarks
            ]
            conn.executemany(
                """
                INSERT INTO country_benchmarks (indicator_id, country_code, country_name, period, value, source_status, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(indicator_id, country_code, period) DO UPDATE SET
                    value = excluded.value,
                    source_status = excluded.source_status,
                    country_name = excluded.country_name,
                    fetched_at = excluded.fetched_at
                """,
                rows,
            )
            return len(rows)
    finally:
        conn.close()


def get_country_benchmarks(
    database_url: str,
    indicator_id: str,
) -> list[dict[str, Any]]:
    """Retrieve stored benchmark observations across countries for a specific indicator."""
    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            rows = conn.execute(
                """
                SELECT indicator_id, country_code, country_name, period, value, source_status, fetched_at
                FROM country_benchmarks
                WHERE indicator_id = ?
                ORDER BY country_code ASC, period ASC
                """,
                (indicator_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_series_status(
    database_url: str,
) -> dict[str, dict[str, Any]]:
    """Get latest run status and observation metadata for every series in the database."""
    conn = get_connection(database_url)
    try:
        with conn:
            init_db(conn)
            # Find the latest run_id per series_id
            rows = conn.execute(
                """
                SELECT qr.id as run_id, qr.series_id, qr.checked_at, qr.observation_count,
                       qr.status, qr.error_count, qr.warning_count, qr.source_url,
                       sm.dataset, sm.unit, sm.dimensions_json
                FROM quality_runs qr
                JOIN (
                    SELECT series_id, MAX(id) as max_id
                    FROM quality_runs
                    GROUP BY series_id
                ) latest ON qr.id = latest.max_id
                LEFT JOIN series_metadata sm ON qr.series_id = sm.series_id
                ORDER BY qr.checked_at DESC
                """
            ).fetchall()

            result: dict[str, dict[str, Any]] = {}
            for r in rows:
                sid = r["series_id"]
                # Also find latest valid period and observation for this run
                latest_obs_row = conn.execute(
                    """
                    SELECT period, value, source_status, fetched_at
                    FROM observations
                    WHERE run_id = ? AND value IS NOT NULL
                    ORDER BY period DESC
                    LIMIT 1
                    """,
                    (r["run_id"],),
                ).fetchone()

                result[sid] = {
                    "run_id": r["run_id"],
                    "series_id": sid,
                    "checked_at": r["checked_at"],
                    "observation_count": r["observation_count"],
                    "status": r["status"],
                    "error_count": r["error_count"],
                    "warning_count": r["warning_count"],
                    "source_url": r["source_url"],
                    "dataset": r["dataset"] or "",
                    "unit": r["unit"] or "",
                    "dimensions": json.loads(r["dimensions_json"]) if r["dimensions_json"] else {},
                    "latest_period": latest_obs_row["period"] if latest_obs_row else None,
                    "latest_value": latest_obs_row["value"] if latest_obs_row else None,
                    "latest_status": latest_obs_row["source_status"] if latest_obs_row else None,
                }
            return result
    finally:
        conn.close()
