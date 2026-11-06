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
from graph import execute_run  # noqa: E402

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
    assert seen == ["v1"] * 5 + ["v2"] * 4

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
        assert conn.execute("SELECT COUNT(*) FROM test_results").fetchone()[0] == 9
        assert conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0] == 4


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
