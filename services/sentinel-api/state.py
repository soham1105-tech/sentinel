"""Typed state passed between Sentinel's LangGraph nodes."""

from __future__ import annotations

from typing import Any, TypedDict


class Scenario(TypedDict):
    id: str
    title: str
    message: str
    expected: str


class TestResult(TypedDict):
    scenario_id: str
    title: str
    message: str
    expected: str
    version: str
    passed: bool
    reply: str
    booked: dict[str, Any] | None
    transcript: str


class PatchRecord(TypedDict):
    scenario_id: str
    diagnosis: str
    patch_text: str


class SentinelState(TypedDict, total=False):
    run_id: str
    target_version: str
    initial_version: str
    scenarios: list[Scenario]
    results: list[TestResult]
    patches: list[PatchRecord]
    score_before: int
    score_after: int
    failures: list[str]
    diagnoses: dict[str, str]
    report: dict[str, Any]
    n8n_status: str
    store_status: dict[str, Any]
