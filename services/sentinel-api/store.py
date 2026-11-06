"""Persistence: Supabase when configured, local SQLite otherwise.

Both backends use the same table and column names. Supabase failures are
logged and fall back to SQLite so a demo never depends on the cloud.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).resolve().parent / "data" / "sentinel.db"

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_version TEXT NOT NULL,
    score_before INTEGER NOT NULL,
    score_after INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS test_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    version TEXT NOT NULL,
    passed INTEGER NOT NULL,
    reply TEXT NOT NULL,
    transcript TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patches (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    scenario_id TEXT NOT NULL,
    patch_text TEXT NOT NULL
);
"""


def _sqlite_path() -> Path:
    configured = os.getenv("SENTINEL_SQLITE_PATH", "").strip()
    return Path(configured).expanduser() if configured else _DEFAULT_DB


def _bootstrap(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SQLITE_SCHEMA)


def save_run(
    run: dict[str, Any],
    results: list[dict[str, Any]],
    patches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Upsert one run plus its evidence. Returns backend metadata."""
    run_row = {
        "id": run["run_id"],
        "target_version": run.get("target_version", "unknown"),
        "score_before": int(run.get("score_before", 0)),
        "score_after": int(run.get("score_after", 0)),
    }
    result_rows = [
        {
            "id": str(uuid4()),
            "run_id": run_row["id"],
            "scenario_id": result["scenario_id"],
            "version": result["version"],
            "passed": bool(result["passed"]),
            "reply": result.get("reply", ""),
            "transcript": result.get("transcript", ""),
        }
        for result in results
    ]
    patch_rows = [
        {
            "id": str(uuid4()),
            "run_id": run_row["id"],
            "scenario_id": patch["scenario_id"],
            "patch_text": patch["patch_text"],
        }
        for patch in patches
    ]

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    supabase_error: str | None = None

    if supabase_url and supabase_key:
        try:
            from supabase import create_client

            client = create_client(supabase_url, supabase_key)
            client.table("runs").upsert(run_row).execute()
            client.table("test_results").delete().eq("run_id", run_row["id"]).execute()
            client.table("patches").delete().eq("run_id", run_row["id"]).execute()
            if result_rows:
                client.table("test_results").insert(result_rows).execute()
            if patch_rows:
                client.table("patches").insert(patch_rows).execute()
            return {"backend": "supabase", "error": None}
        except Exception as exc:  # noqa: BLE001 - fall back locally
            supabase_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Supabase unavailable, using SQLite: %s", supabase_error)

    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(path) as conn:
            _bootstrap(conn)
            conn.execute(
                """
                INSERT INTO runs (id, target_version, score_before, score_after)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    target_version = excluded.target_version,
                    score_before = excluded.score_before,
                    score_after = excluded.score_after
                """,
                (
                    run_row["id"],
                    run_row["target_version"],
                    run_row["score_before"],
                    run_row["score_after"],
                ),
            )
            conn.execute("DELETE FROM test_results WHERE run_id = ?", (run_row["id"],))
            conn.execute("DELETE FROM patches WHERE run_id = ?", (run_row["id"],))
            conn.executemany(
                """
                INSERT INTO test_results
                    (id, run_id, scenario_id, version, passed, reply, transcript)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["id"],
                        row["run_id"],
                        row["scenario_id"],
                        row["version"],
                        int(row["passed"]),
                        row["reply"],
                        row["transcript"],
                    )
                    for row in result_rows
                ],
            )
            conn.executemany(
                """
                INSERT INTO patches (id, run_id, scenario_id, patch_text)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (row["id"], row["run_id"], row["scenario_id"], row["patch_text"])
                    for row in patch_rows
                ],
            )
            conn.commit()
        return {
            "backend": "sqlite",
            "path": str(path),
            "error": supabase_error,
        }
    except Exception as exc:  # noqa: BLE001 - report persistence error, not a crash
        error = f"SQLite save failed: {type(exc).__name__}: {exc}"
        logger.error(error)
        return {"backend": "none", "error": error}


def list_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Return the newest runs from the same backend used by save_run."""
    limit = max(1, min(int(limit), 50))
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )

    if supabase_url and supabase_key:
        try:
            from supabase import create_client

            client = create_client(supabase_url, supabase_key)
            response = (
                client.table("runs")
                .select("id,created_at,target_version,score_before,score_after")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [
                {
                    "run_id": row["id"],
                    "created_at": row.get("created_at"),
                    "target_version": row.get("target_version"),
                    "score_before": row.get("score_before"),
                    "score_after": row.get("score_after"),
                }
                for row in (response.data or [])
            ]
        except Exception as exc:  # noqa: BLE001 - fall back locally
            logger.warning("Supabase run list unavailable, using SQLite: %s", exc)

    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(path) as conn:
            _bootstrap(conn)
            rows = conn.execute(
                """
                SELECT id, created_at, target_version, score_before, score_after
                FROM runs
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "run_id": row[0],
                "created_at": row[1],
                "target_version": row[2],
                "score_before": row[3],
                "score_after": row[4],
            }
            for row in rows
        ]
    except Exception as exc:  # noqa: BLE001 - history is optional, never break a run
        logger.error("SQLite run list failed: %s", exc)
        return []
