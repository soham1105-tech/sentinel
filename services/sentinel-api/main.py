"""SENTINEL API: create a run, read it, re-test, or summarize trends."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from graph import (
    ADAPTIVE_TEMPLATES,
    ALL_SCENARIO_IDS,
    DIAGNOSES,
    FIRST_FIVE_IDS,
    SCENARIOS,
    RuntimeConfig,
    _assemble_report,
    execute_run,
    retest_run,
)
from llm import fallback_report
from store import get_run as get_stored_run
from store import list_runs as list_recent_runs_from_store
from store import recent_runs_with_results


RUN_TIMEOUT_SECONDS = 120.0

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


def _infer_initial_version(tests: list[dict[str, Any]], target_version: str) -> str:
    versions = [str(item.get("version", "")) for item in tests]
    return next(
        (version for version in versions if version and version != target_version),
        versions[0] if versions else target_version,
    )


def _as_test_result(
    item: dict[str, Any],
    scenario_id: str,
    title: str,
    message: str,
    expected: str,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "title": title,
        "message": message,
        "expected": expected,
        "version": str(item.get("version", "")),
        "passed": bool(item.get("passed", False)),
        "reply": str(item.get("reply", "") or ""),
        "booked": None,
        "transcript": str(item.get("transcript", "") or ""),
    }


def _state_from_stored(stored: dict[str, Any]) -> dict[str, Any]:
    run = stored["run"]
    scenario_by_id = {scenario["id"]: scenario for scenario in SCENARIOS}
    parent_tests: list[dict[str, Any]] = []
    adaptive_tests: list[dict[str, Any]] = []
    regression_tests: list[dict[str, Any]] = []

    for item in stored["tests"]:
        sid = str(item.get("scenario_id", ""))
        if sid in scenario_by_id:
            scenario = scenario_by_id[sid]
            parent_tests.append(
                _as_test_result(
                    item,
                    sid,
                    scenario["title"],
                    scenario["message"],
                    scenario["expected"],
                )
            )
        elif "-V" in sid:
            parent_id = sid.split("-V", 1)[0]
            parent = scenario_by_id.get(parent_id)
            message = ADAPTIVE_TEMPLATES.get(
                parent_id,
                parent["message"] if parent else "",
            )
            adaptive_tests.append(
                _as_test_result(
                    item,
                    sid,
                    f"Adaptive probe: {parent['title']}" if parent else "Adaptive probe",
                    message,
                    parent["expected"] if parent else "",
                )
            )
        elif sid.startswith("REG-"):
            parent_id = sid[4:]
            parent = scenario_by_id.get(parent_id)
            regression_tests.append(
                _as_test_result(
                    item,
                    sid,
                    f"Regression guard: {parent['title']}" if parent else "Regression guard",
                    parent["message"] if parent else "",
                    parent["expected"] if parent else "",
                )
            )

    patches = [
        {
            "scenario_id": str(item.get("scenario_id", "")),
            "diagnosis": DIAGNOSES.get(
                str(item.get("scenario_id", "")), "No fixed diagnosis."
            ),
            "patch_text": str(item.get("patch_text", "") or ""),
        }
        for item in stored["patches"]
    ]
    first_five_ids = set(FIRST_FIVE_IDS)
    target_version = str(run.get("target_version") or "")
    initial_version = _infer_initial_version(parent_tests, target_version)
    regression_checked = [
        result["scenario_id"][4:]
        for result in regression_tests
        if result["scenario_id"].startswith("REG-")
    ]

    return {
        "run_id": str(run.get("run_id", "")),
        "target_version": target_version,
        "initial_version": initial_version,
        "full_results": parent_tests,
        "results": [
            result
            for result in parent_tests
            if result["scenario_id"] in first_five_ids
        ],
        "adaptive_results": adaptive_tests,
        "regression_results": regression_tests,
        "regression_checked": regression_checked,
        "regression_setup_transcript": "",
        "full_patches": patches,
        "patches": [
            patch for patch in patches if patch["scenario_id"] in first_five_ids
        ],
        "diagnoses": {
            scenario_id: DIAGNOSES[scenario_id]
            for scenario_id in DIAGNOSES
        },
        "score_before": int(run.get("score_before", 0)),
        "score_after": int(run.get("score_after", 0)),
    }


def _report_from_storage(run_id: str) -> dict[str, Any] | None:
    """Rebuild the advanced report from persisted rows without inventing verdicts."""
    stored = get_stored_run(run_id)
    if stored is None:
        return None

    state = _state_from_stored(stored)
    report = _assemble_report(state)
    report["created_at"] = stored["run"].get("created_at") or ""
    report["storage"] = {"backend": stored["backend"], "error": None}
    report["n8n_status"] = "not recorded (rebuilt from storage)"
    report["narrative"] = fallback_report(
        {
            "run_id": report["run_id"],
            "score_before_label": report["score_before_label"],
            "score_after_label": report["score_after_label"],
            "failures": report["failures"],
            "patches": report["patches"],
        }
    )
    report["narrative_source"] = "deterministic (rebuilt from storage)"
    return report


def _summary_payload() -> dict[str, Any]:
    records = recent_runs_with_results(limit=10)
    runs_payload: list[dict[str, Any]] = []
    stats = {
        scenario["id"]: {
            "scenario_id": scenario["id"],
            "title": scenario["title"],
            "runs": 0,
            "passed_before": 0,
            "passed_after": 0,
        }
        for scenario in SCENARIOS
    }

    for stored in records:
        run = stored["run"]
        parent_tests = [
            result
            for result in stored["tests"]
            if result.get("scenario_id") in ALL_SCENARIO_IDS
        ]
        target_version = str(run.get("target_version") or "")
        initial_version = _infer_initial_version(parent_tests, target_version)
        initial = [
            result for result in parent_tests if result.get("version") == initial_version
        ]
        retests: dict[str, dict[str, Any]] = {}
        for result in parent_tests:
            if result.get("version") != initial_version:
                retests[str(result.get("scenario_id"))] = result

        initial_by_id = {str(result.get("scenario_id")): result for result in initial}
        before = sum(1 for result in initial if result.get("passed"))
        after = 0
        for scenario in SCENARIOS:
            sid = scenario["id"]
            first = initial_by_id.get(sid)
            if first is None:
                continue
            final = first if first.get("passed") else retests.get(sid, first)
            if final.get("passed"):
                after += 1
            stats[sid]["runs"] += 1
            if first.get("passed"):
                stats[sid]["passed_before"] += 1
            if final.get("passed"):
                stats[sid]["passed_after"] += 1

        total = len(initial_by_id)
        before_label, before_percent = _score_label(int(before), total)
        after_label, after_percent = _score_label(int(after), total)
        runs_payload.append(
            {
                "run_id": run.get("run_id"),
                "created_at": run.get("created_at"),
                "score_before": int(run.get("score_before", 0)),
                "score_after": int(run.get("score_after", 0)),
                "full_suite_before": int(before),
                "full_suite_after": int(after),
                "full_suite_total": total,
                "full_suite_before_label": before_label,
                "full_suite_after_label": after_label,
                "full_suite_before_percent": before_percent,
                "full_suite_after_percent": after_percent,
            }
        )

    per_scenario = []
    for scenario in SCENARIOS:
        row = stats[scenario["id"]]
        countable = int(row["runs"])
        per_scenario.append(
            {
                **row,
                "pass_rate_before": round(
                    (row["passed_before"] / countable) * 100
                )
                if countable
                else 0,
                "pass_rate_after": round(
                    (row["passed_after"] / countable) * 100
                )
                if countable
                else 0,
            }
        )

    return {"runs": runs_payload, "per_scenario": per_scenario}


@app.post("/v1/runs")
async def create_run() -> dict[str, Any]:
    try:
        state = await asyncio.wait_for(
            execute_run(), timeout=RUN_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=500, detail="run timed out") from exc
    _RUNS[state["run_id"]] = state
    return _public(state)


@app.get("/v1/runs")
def list_runs() -> list[dict[str, Any]]:
    return list_recent_runs_from_store(limit=10)


@app.get("/v1/runs/summary")
def runs_summary() -> dict[str, Any]:
    return _summary_payload()


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
    try:
        updated = await asyncio.wait_for(
            retest_run(state, RuntimeConfig()), timeout=RUN_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=500, detail="run timed out") from exc
    _RUNS[run_id] = updated
    return _public(updated)
