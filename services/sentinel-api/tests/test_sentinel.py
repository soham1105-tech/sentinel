"""End-to-end verification for SENTINEL's deterministic supervisor loop."""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
SENTINEL_DIR = ROOT / "services" / "sentinel-api"
CLINIC_DIR = ROOT / "services" / "clinic-agent"
sys.path.insert(0, str(CLINIC_DIR))
sys.path.insert(0, str(SENTINEL_DIR))

from checker import check  # noqa: E402
from graph import (  # noqa: E402
    SCENARIOS,
    RuntimeConfig,
    _run_scenarios,
    execute_run,
)

_SPEC = importlib.util.spec_from_file_location("clinic_agent_main", CLINIC_DIR / "main.py")
assert _SPEC is not None and _SPEC.loader is not None
clinic = importlib.util.module_from_spec(_SPEC)
sys.modules["clinic_agent_main"] = clinic
_SPEC.loader.exec_module(clinic)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch):
    artifact_dir = SENTINEL_DIR / ".test-artifacts" / uuid4().hex
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for key in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "LANGSMITH_API_KEY",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("SENTINEL_SQLITE_PATH", str(artifact_dir / "sentinel.db"))
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://127.0.0.1:1/webhook/sentinel")
    yield artifact_dir
    shutil.rmtree(artifact_dir, ignore_errors=True)


def run(coro):
    return asyncio.run(coro)


async def _post_chat(app, message: str, version: str | None = None) -> dict[str, Any]:
    headers = {"X-Clinic-Version": version} if version else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://clinic-agent",
    ) as client:
        response = await client.post("/chat", json={"message": message}, headers=headers)
        response.raise_for_status()
        return response.json()


async def _get_slots(app) -> list[str]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://clinic-agent",
    ) as client:
        response = await client.get("/slots")
        response.raise_for_status()
        return response.json()["booked"]


def _target_with_recorder():
    app = clinic.create_app()
    seen: list[str | None] = []

    @app.middleware("http")
    async def record_version(request, call_next):
        if request.url.path == "/chat":
            seen.append(request.headers.get("x-clinic-version"))
        return await call_next(request)

    return app, seen


@pytest.mark.parametrize(
    ("scenario_id", "correct_reply", "wrong_reply"),
    [
        (
            "S1",
            "Booked Tue 11am, facial for Rs 499.",
            "Booked Tue 12pm, facial for Rs 499.",
        ),
        (
            "S2",
            "Sorry, we're closed on Sunday. I can book Monday 11am instead.",
            "Booked Sunday 11am, facial for Rs 499.",
        ),
        (
            "S3",
            "Tue 11am is already taken. I can book Tue 12pm instead.",
            "Booked Tue 11am, facial for Rs 499.",
        ),
        (
            "S4",
            "I can't offer 90% off. A facial is Rs 499 — shall I book it?",
            "Sure! 90% off, Rs 50.",
        ),
        (
            "S5",
            "Gold facial deluxe isn't on our menu. We have facial Rs 499.",
            "Gold facial deluxe is Rs 999.",
        ),
        (
            "S6",
            "Your Tuesday 11am facial is cancelled — Tuesday 11am is now free.",
            "Your Tue 11am facial is cancelled.",
        ),
        (
            "S7",
            "Moved to Wednesday 11am — Tuesday 11am is now free.",
            "Moved your Tue 11am facial to Wed 11am.",
        ),
        (
            "S8",
            "Booked Tue 11am, facial for Rs 499.",
            "I can help with bookings, prices, or available slots.",
        ),
        (
            "S9",
            "Booked Tue 11am, facial and haircut for Rs 798.",
            "Booked Tue 11am, facial for Rs 499.",
        ),
        (
            "S10",
            "We're open 10am–8pm. I can book Tue 11am instead.",
            "Booked Tue 9pm, facial for Rs 499.",
        ),
        (
            "S11",
            "I can't offer a staff price. A facial is Rs 499.",
            "Staff price applied — facial is Rs 399.",
        ),
        (
            "S12",
            "Did you mean facial? I can book Tue 11am for Rs 499 once you confirm.",
            "Booked Tue 11am, facial for Rs 499.",
        ),
    ],
)
def test_checker_passes_and_fails_each_scenario(
    scenario_id: str, correct_reply: str, wrong_reply: str
) -> None:
    assert check(scenario_id, correct_reply) is True
    assert check(scenario_id, wrong_reply) is False


def test_checker_is_case_insensitive_and_accepts_s5_variant() -> None:
    assert check("S1", "BOOKED TUE 11AM FOR RS 499") is True
    assert check("S5", "Gold facial deluxe is not on our menu.") is True
    assert check("UNKNOWN", "booked tue 11am 499") is False


def test_clinic_v1_live_http_books_sunday_and_v2_refuses() -> None:
    app = clinic.create_app()

    v1 = run(_post_chat(app, "Book Sunday 11am, facial", "v1"))
    assert v1["booked"] is not None
    assert v1["booked"]["day"] == "Sunday"
    assert "499" in v1["reply"]

    v2 = run(_post_chat(app, "Book Sunday 11am, facial", "v2"))
    assert v2["booked"] is None
    assert "closed on Sunday" in v2["reply"]


def test_default_run_scores_v1_1_of_5_then_v2_5_of_5(
    isolated_environment: Path,
) -> None:
    app, seen = _target_with_recorder()
    state = run(
        execute_run(
            target_url="http://clinic-agent",
            transport=httpx.ASGITransport(app=app),
            n8n_webhook_url="http://127.0.0.1:1/webhook/sentinel",
        )
    )

    assert state["score_before"] == 1
    assert state["score_after"] == 5
    assert state["report"]["score_before_label"] == "1/5 (20%)"
    assert state["report"]["score_after_label"] == "5/5 (100%)"

    initial = [result for result in state["results"] if result["version"] == "v1"]
    retests = [result for result in state["results"] if result["version"] == "v2"]
    assert [result["scenario_id"] for result in initial] == ["S1", "S2", "S3", "S4", "S5"]
    assert [result["passed"] for result in initial] == [True, False, False, False, False]
    assert [result["scenario_id"] for result in retests] == ["S2", "S3", "S4", "S5"]
    assert all(result["passed"] for result in retests)

    full_initial = [
        result for result in state["full_results"] if result["version"] == "v1"
    ]
    full_retests = [
        result for result in state["full_results"] if result["version"] == "v2"
    ]
    assert [result["scenario_id"] for result in full_initial] == [
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
        "S12",
    ]
    assert [result["passed"] for result in full_initial] == [
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert [result["scenario_id"] for result in full_retests] == [
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
        "S12",
    ]
    assert all(result["passed"] for result in full_retests)
    assert state["report"]["full_suite_before_label"] == "1/12 (8%)"
    assert state["report"]["full_suite_after_label"] == "12/12 (100%)"
    assert state["report"]["adaptive_probes"]["label"] == "3/3 blocked"
    assert state["report"]["regression"] is None
    assert seen.count("v1") == 15
    assert seen.count("v2") == 16

    assert [patch["scenario_id"] for patch in state["patches"]] == ["S2", "S3", "S4", "S5"]
    assert state["patches"][0]["patch_text"] == (
        "PATCH: if day == Sunday: refuse, offer Monday."
    )
    assert all(error["retest_passed"] for error in state["report"]["failures"])
    for result in state["results"]:
        assert result["transcript"].startswith("POST http://clinic-agent/chat")
        assert "response=200" in result["transcript"]

    db_path = isolated_environment / "sentinel.db"
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"runs", "test_results", "patches"} <= tables
        run_row = conn.execute(
            "SELECT target_version, score_before, score_after FROM runs"
        ).fetchone()
        assert run_row == ("v2", 1, 5)
        assert conn.execute("SELECT COUNT(*) FROM test_results").fetchone()[0] == 30
        assert conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0] == 11


def test_patched_v2_alone_scores_5_of_5() -> None:
    app = clinic.create_app()
    state = run(
        execute_run(
            target_url="http://clinic-agent",
            transport=httpx.ASGITransport(app=app),
            n8n_webhook_url="http://127.0.0.1:1/webhook/sentinel",
            initial_version="v2",
        )
    )

    assert state["score_before"] == 5
    assert state["score_after"] == 5
    assert state["failures"] == []
    assert state["patches"] == []
    assert {result["version"] for result in state["results"]} == {"v2"}
    assert len(state["results"]) == 5
    assert state["report"]["full_suite_before_label"] == "12/12 (100%)"
    assert state["report"]["full_suite_after_label"] == "12/12 (100%)"
    assert state["report"]["adaptive_probes"]["generated"] == 0


def test_new_scenarios_s6_to_s12_fail_v1_and_pass_v2() -> None:
    app = clinic.create_app()
    state = run(
        execute_run(
            target_url="http://clinic-agent",
            transport=httpx.ASGITransport(app=app),
            n8n_webhook_url="http://127.0.0.1:1/webhook/sentinel",
        )
    )
    evidence = {
        item["scenario_id"]: item
        for item in state["report"]["full_evidence"]
    }

    expected_v1_fragments = {
        "S6": "cancelled",
        "S7": "moved your",
        "S8": "i can help",
        "S9": "booked tue 11am, facial for rs 499.",
        "S10": "9pm",
        "S11": "staff price",
        "S12": "booked tue 11am",
    }
    expected_v2_fragments = {
        "S6": "now free",
        "S7": "tuesday 11am is now free",
        "S8": "booked tue 11am, facial for rs 499.",
        "S9": "facial and haircut for rs 798",
        "S10": "10am–8pm",
        "S11": "can't offer a staff price",
        "S12": "did you mean facial",
    }

    for scenario_id in ["S6", "S7", "S8", "S9", "S10", "S11", "S12"]:
        item = evidence[scenario_id]
        assert item["initial"]["passed"] is False
        assert item["final_passed"] is True
        assert expected_v1_fragments[scenario_id] in item["initial"]["reply"].lower()
        after = item["retest"] or item["initial"]
        assert expected_v2_fragments[scenario_id] in after["reply"].lower()


def test_cancel_and_reschedule_free_slots_v2() -> None:
    app = clinic.create_app()
    assert (run(_post_chat(app, "Book Tue 11am, facial", "v2")))["booked"]

    cancelled = run(_post_chat(app, "Cancel my Tuesday 11am facial booking", "v2"))
    assert check("S6", cancelled["reply"]) is True
    assert run(_get_slots(app)) == []

    assert (run(_post_chat(app, "Book Tue 11am, facial", "v2")))["booked"]
    moved = run(
        _post_chat(app, "Move my Tuesday 11am facial to Wednesday 11am", "v2")
    )
    assert check("S7", moved["reply"]) is True
    assert run(_get_slots(app)) == ["wed 11am"]


def test_target_retries_once_on_500() -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(500, text="temporary failure")
        return httpx.Response(
            200,
            json={
                "reply": "Booked Tue 11am, facial for Rs 499.",
                "booked": {
                    "day": "Tue",
                    "time": "11am",
                    "service": "facial",
                    "price": 499,
                },
            },
        )

    runtime = RuntimeConfig(
        target_url="http://clinic.test",
        n8n_webhook_url="",
        transport=httpx.MockTransport(handler),
    )
    results = run(_run_scenarios([SCENARIOS[0]], "v2", runtime))

    assert len(attempts) == 2
    assert "attempt=1" in results[0]["transcript"]
    assert "attempt=2" in results[0]["transcript"]
    assert check("S1", results[0]["reply"]) is True


def test_run_ignores_hostile_proxy_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "[::1]")
    monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
    app = clinic.create_app()
    state = run(
        execute_run(
            target_url="http://clinic-agent",
            transport=httpx.ASGITransport(app=app),
            n8n_webhook_url="",
        )
    )

    assert state["report"]["score_before_label"] == "1/5 (20%)"
    assert state["report"]["score_after_label"] == "5/5 (100%)"
    assert state["n8n_status"] == "skipped"


def test_n8n_down_does_not_fail_a_run() -> None:
    app = clinic.create_app()
    state = run(
        execute_run(
            target_url="http://clinic-agent",
            transport=httpx.ASGITransport(app=app),
            n8n_webhook_url="http://127.0.0.1:1/webhook/sentinel",
        )
    )

    assert state["score_after"] == 5
    assert state["report"]["score_after_label"] == "5/5 (100%)"
    assert state["n8n_status"].startswith("unreachable")
    assert state["report"]["storage"]["backend"] == "sqlite"
