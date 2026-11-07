"""API-level tests against FastAPI, using a self-hosted local clinic target."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

import pytest
import uvicorn
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
SENTINEL_DIR = ROOT / "services" / "sentinel-api"
CLINIC_DIR = ROOT / "services" / "clinic-agent"
sys.path.insert(0, str(CLINIC_DIR))
sys.path.insert(0, str(SENTINEL_DIR))

import main as sentinel_api  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "clinic_agent_api_main", CLINIC_DIR / "main.py"
)
assert _SPEC is not None and _SPEC.loader is not None
clinic = importlib.util.module_from_spec(_SPEC)
sys.modules["clinic_agent_api_main"] = clinic
_SPEC.loader.exec_module(clinic)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def clinic_url() -> Iterator[str]:
    """Run the simulated target on a temporary local HTTP port."""
    port = _free_port()
    config = uvicorn.Config(
        clinic.create_app(),
        host="127.0.0.1",
        port=port,
        log_level="error",
        lifespan="off",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Clinic test server did not start")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def isolated_api(
    monkeypatch: pytest.MonkeyPatch, clinic_url: str
) -> Iterator[Path]:
    artifact_dir = SENTINEL_DIR / ".test-artifacts" / f"api-{uuid4().hex}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SENTINEL_SQLITE_PATH", str(artifact_dir / "sentinel.db"))
    monkeypatch.setenv("CLINIC_AGENT_URL", clinic_url)
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://127.0.0.1:1/webhook/sentinel")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    for key in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "LANGSMITH_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    sentinel_api._RUNS.clear()
    try:
        yield artifact_dir
    finally:
        sentinel_api._RUNS.clear()
        shutil.rmtree(artifact_dir, ignore_errors=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(sentinel_api.app) as test_client:
        yield test_client


def _create_run(client: TestClient) -> dict[str, Any]:
    response = client.post("/v1/runs")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    return payload


def test_post_run_returns_measured_report(client: TestClient) -> None:
    payload = _create_run(client)

    assert payload["score_before"] == 1
    assert payload["score_after"] == 5
    assert payload["score_before_label"] == "1/5 (20%)"
    assert payload["score_after_label"] == "5/5 (100%)"
    assert len(payload["tests"]) == 9
    assert len(payload["patches"]) == 4
    assert len(payload["evidence"]) == 5
    assert len(payload["failures"]) == 4
    assert payload["full_suite_before_label"] == "1/12 (8%)"
    assert payload["full_suite_after_label"] == "12/12 (100%)"
    assert len(payload["full_evidence"]) == 12
    assert len(payload["full_patches"]) == 11
    assert payload["adaptive_probes"]["label"] == "3/3 blocked"
    assert payload["severity"]["before"] == {
        "Critical": 3,
        "High": 5,
        "Medium": 3,
    }
    assert payload["regression"] is None


def test_get_runs_lists_the_created_run(client: TestClient) -> None:
    created = _create_run(client)
    response = client.get("/v1/runs")

    assert response.status_code == 200
    runs = response.json()
    assert any(run["run_id"] == created["run_id"] for run in runs)


def test_get_run_returns_the_same_completed_run(client: TestClient) -> None:
    created = _create_run(client)
    response = client.get(f"/v1/runs/{created['run_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == created["run_id"]
    assert payload["score_before_label"] == "1/5 (20%)"
    assert payload["score_after_label"] == "5/5 (100%)"
    assert len(payload["tests"]) == 9
    assert len(payload["patches"]) == 4


def test_get_unknown_run_returns_404(client: TestClient) -> None:
    response = client.get("/v1/runs/does-not-exist")
    assert response.status_code == 404


def test_retest_returns_measured_same_run(client: TestClient) -> None:
    created = _create_run(client)
    response = client.post(f"/v1/runs/{created['run_id']}/retest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == created["run_id"]
    assert payload["score_before_label"] == "1/5 (20%)"
    assert payload["score_after_label"] == "5/5 (100%)"
    assert len(payload["tests"]) == 9
    assert len(payload["patches"]) == 4


def test_cors_allows_dashboard_origin(client: TestClient) -> None:
    origin = "http://localhost:3000"
    response = client.get("/v1/runs", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin

    preflight = client.options(
        "/v1/runs",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin


def test_run_detail_survives_in_memory_restart(
    client: TestClient,
) -> None:
    created = _create_run(client)

    sentinel_api._RUNS.clear()
    response = client.get(f"/v1/runs/{created['run_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == created["run_id"]
    assert payload["score_before_label"] == "1/5 (20%)"
    assert payload["score_after_label"] == "5/5 (100%)"
    assert len(payload["tests"]) == 9
    assert len(payload["patches"]) == 4
    assert payload["storage"]["backend"] == "sqlite"
    assert payload["narrative_source"] == "deterministic (rebuilt from storage)"
    assert payload["full_suite_after_label"] == "12/12 (100%)"
    assert len(payload["full_evidence"]) == 12
    assert payload["adaptive_probes"]["label"] == "3/3 blocked"
    assert payload["severity"]["before"]["Critical"] == 3


def test_retest_after_restart_requires_new_session(client: TestClient) -> None:
    created = _create_run(client)
    sentinel_api._RUNS.clear()

    response = client.post(f"/v1/runs/{created['run_id']}/retest")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Run not found in this server session — press Run Sentinel to create a new run"
    )


def test_regression_guard_checks_first_run_passes(client: TestClient) -> None:
    payload = _create_run(client)

    assert payload["regression"] is None
    assert payload["regression_checked"] == ["S1"]
    assert len(payload["regression_results"]) == 1
    assert payload["regression_results"][0]["scenario_id"] == "REG-S1"
    assert payload["regression_results"][0]["passed"] is True


def test_runs_summary_returns_full_suite_and_pass_rates(
    client: TestClient,
) -> None:
    created = _create_run(client)
    response = client.get("/v1/runs/summary")

    assert response.status_code == 200
    summary = response.json()
    assert len(summary["runs"]) == 1
    point = summary["runs"][0]
    assert point["run_id"] == created["run_id"]
    assert point["score_before"] == 1
    assert point["score_after"] == 5
    assert point["full_suite_before"] == 1
    assert point["full_suite_after"] == 12
    assert point["full_suite_total"] == 12
    assert len(summary["per_scenario"]) == 12
    s2 = next(
        row for row in summary["per_scenario"] if row["scenario_id"] == "S2"
    )
    assert s2["pass_rate_before"] == 0
    assert s2["pass_rate_after"] == 100


def test_run_survives_hostile_proxy_and_skips_unset_n8n(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "[::1]")
    monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)

    payload = _create_run(client)

    assert payload["score_before_label"] == "1/5 (20%)"
    assert payload["score_after_label"] == "5/5 (100%)"
    assert payload["n8n_status"] == "skipped"


def test_run_timeout_returns_clean_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def slow_run() -> dict[str, Any]:
        await asyncio.sleep(0.2)
        return {}

    monkeypatch.setattr(sentinel_api, "RUN_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(sentinel_api, "execute_run", slow_run)

    response = client.post("/v1/runs")

    assert response.status_code == 500
    assert response.json() == {"detail": "run timed out"}
