"""SENTINEL API: create a run, read it, or re-test its failures."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from graph import RuntimeConfig, execute_run, retest_run
from store import list_runs as list_recent_runs_from_store


app = FastAPI(
    title="SENTINEL API",
    description="Supervisor agent that tests, diagnoses, patches, and re-tests AI agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_RUNS: dict[str, dict[str, Any]] = {}


def _public(state: dict[str, Any]) -> dict[str, Any]:
    report = state.get("report", {})
    return {"status": "completed", **report}


@app.post("/v1/runs")
async def create_run() -> dict[str, Any]:
    state = await execute_run()
    _RUNS[state["run_id"]] = state
    return _public(state)


@app.get("/v1/runs")
def list_runs() -> list[dict[str, Any]]:
    return list_recent_runs_from_store(limit=10)


@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _public(state)


@app.post("/v1/runs/{run_id}/retest")
async def retest_run_endpoint(run_id: str) -> dict[str, Any]:
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    updated = await retest_run(state, RuntimeConfig())
    _RUNS[run_id] = updated
    return _public(updated)
