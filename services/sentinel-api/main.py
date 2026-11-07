"""SENTINEL API: create a run, read it, or re-test its failures."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from graph import DIAGNOSES, SCENARIOS, RuntimeConfig, execute_run, retest_run
from llm import fallback_report
from store import get_run as get_stored_run
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


def _score_label(passed: int, total: int) -> tuple[str, int]:
    percent = round((passed / total) * 100) if total else 0
    return f"{passed}/{total} ({percent}%)", percent


def _report_from_storage(run_id: str) -> dict[str, Any] | None:
    """Rebuild the report shape from persisted rows without inventing verdicts."""
    stored = get_stored_run(run_id)
    if stored is None:
        return None

    run = stored["run"]
    scenario_by_id = {scenario["id"]: scenario for scenario in SCENARIOS}
    total = len(SCENARIOS)
    raw_tests = stored["tests"]
    versions = [str(item.get("version", "")) for item in raw_tests]
    target_version = str(run.get("target_version") or "")
    initial_version = next(
        (version for version in versions if version and version != target_version),
        versions[0] if versions else target_version,
    )

    tests: list[dict[str, Any]] = []
    for item in raw_tests:
        scenario_id = str(item.get("scenario_id", ""))
        scenario = scenario_by_id.get(scenario_id, {})
        tests.append(
            {
                "scenario_id": scenario_id,
                "title": scenario.get("title", scenario_id or "Unknown scenario"),
                "message": scenario.get("message", ""),
                "expected": scenario.get("expected", ""),
                "version": str(item.get("version", "")),
                "passed": bool(item.get("passed", False)),
                "reply": str(item.get("reply", "") or ""),
                "booked": None,
                "transcript": str(item.get("transcript", "") or ""),
            }
        )

    initial_results = [
        test for test in tests if test["version"] == initial_version
    ]
    retest_results = [
        test for test in tests if test["version"] != initial_version
    ]
    initial_by_id = {test["scenario_id"]: test for test in initial_results}
    latest_retest: dict[str, dict[str, Any]] = {}
    for test in retest_results:
        latest_retest[test["scenario_id"]] = test

    evidence: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        scenario_id = scenario["id"]
        initial = initial_by_id.get(scenario_id)
        retest = latest_retest.get(scenario_id)
        final = initial if initial and initial["passed"] else (retest or initial)
        evidence.append(
            {
                "scenario_id": scenario_id,
                "title": scenario["title"],
                "message": scenario["message"],
                "expected": scenario["expected"],
                "initial": initial,
                "retest": retest,
                "final_passed": bool(final and final["passed"]),
            }
        )

    patch_rows = stored["patches"]
    patches = [
        {
            "scenario_id": str(item.get("scenario_id", "")),
            "diagnosis": DIAGNOSES.get(
                str(item.get("scenario_id", "")), "No fixed diagnosis."
            ),
            "patch_text": str(item.get("patch_text", "") or ""),
        }
        for item in patch_rows
    ]

    failures: list[dict[str, Any]] = []
    for initial in initial_results:
        if initial["passed"]:
            continue
        scenario_id = initial["scenario_id"]
        failures.append(
            {
                "scenario_id": scenario_id,
                "title": initial["title"],
                "expected": initial["expected"],
                "v1_reply": initial["reply"],
                "diagnosis": DIAGNOSES.get(scenario_id, "No fixed diagnosis."),
                "patch_text": next(
                    (
                        patch["patch_text"]
                        for patch in patches
                        if patch["scenario_id"] == scenario_id
                    ),
                    "",
                ),
                "retest_passed": bool(
                    latest_retest.get(scenario_id, {}).get("passed", False)
                ),
            }
        )

    score_before = int(run.get("score_before", 0))
    score_after = int(run.get("score_after", 0))
    before_label, before_percent = _score_label(score_before, total)
    after_label, after_percent = _score_label(score_after, total)
    facts = {
        "run_id": str(run.get("run_id", run_id)),
        "score_before": score_before,
        "score_before_label": before_label,
        "score_after": score_after,
        "score_after_label": after_label,
        "failures": failures,
        "patches": patches,
    }

    return {
        "run_id": str(run.get("run_id", run_id)),
        "created_at": run.get("created_at") or "",
        "target": "clinic-agent",
        "method": "black-box HTTP only",
        "target_version_before": initial_version,
        "target_version_after": target_version or initial_version,
        "score_before": score_before,
        "score_before_percent": before_percent,
        "score_before_label": before_label,
        "score_after": score_after,
        "score_after_percent": after_percent,
        "score_after_label": after_label,
        "failures": failures,
        "patches": patches,
        "tests": tests,
        "evidence": evidence,
        "storage": {"backend": stored["backend"], "error": None},
        "n8n_status": "not recorded (rebuilt from storage)",
        "narrative": fallback_report(facts),
        "narrative_source": "deterministic (rebuilt from storage)",
    }


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
    if state is not None:
        return _public(state)

    rebuilt = _report_from_storage(run_id)
    if rebuilt is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "completed", **rebuilt}


@app.post("/v1/runs/{run_id}/retest")
async def retest_run_endpoint(run_id: str) -> dict[str, Any]:
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Run not found in this server session — press Run Sentinel "
                "to create a new run"
            ),
        )
    updated = await retest_run(state, RuntimeConfig())
    _RUNS[run_id] = updated
    return _public(updated)
