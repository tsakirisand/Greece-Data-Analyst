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


def init_db(connection: sqlite3.Connection) -> None:
    """Create schema tables and indices if not already present."""
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

        CREATE INDEX IF NOT EXISTS idx_observations_series_period
            ON observations(series_id, period);
        CREATE INDEX IF NOT EXISTS idx_quality_runs_series
            ON quality_runs(series_id, checked_at);
        CREATE INDEX IF NOT EXISTS idx_quality_findings_run
            ON quality_findings(run_id);
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
