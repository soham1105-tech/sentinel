#!/usr/bin/env python3
"""Run the complete SENTINEL loop with no server and no API keys.

The clinic target is still exercised over HTTP through httpx.ASGITransport.
It is never called in-process as a Python function.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SENTINEL_DIR = ROOT / "services" / "sentinel-api"
CLINIC_DIR = ROOT / "services" / "clinic-agent"
sys.path.insert(0, str(SENTINEL_DIR))
sys.path.insert(0, str(CLINIC_DIR))

from graph import execute_run  # noqa: E402


def load_clinic_app():
    """Load the target app for ASGI transport; Sentinel still speaks HTTP."""
    module_path = CLINIC_DIR / "main.py"
    spec = importlib.util.spec_from_file_location("clinic_agent_main", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load clinic target from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["clinic_agent_main"] = module
    spec.loader.exec_module(module)
    return module.create_app()


def _print_result(label: str, result: dict) -> None:
    status = "PASS" if result["passed"] else "FAIL"
    print(f"[{label}] {result['scenario_id']} {status} | {result['transcript']}")


async def main() -> int:
    target_app = load_clinic_app()
    transport = httpx.ASGITransport(app=target_app)

    print("SENTINEL — supervisor agent for clinic-agent (black-box HTTP)")
    print("Target runs in-process only as an ASGI HTTP transport; there is no server dependency.")
    print()

    state = await execute_run(
        target_url="http://clinic-agent",
        transport=transport,
    )
    report = state["report"]

    for result in report["tests"]:
        if result["version"] == report["target_version_before"]:
            _print_result("v1 initial", result)

    print()
    print(f"SCORE BEFORE: {report['score_before_label']}")

    if report["patches"]:
        print("\nDIAGNOSES + PATCHES")
        for failure in report["failures"]:
            print(f"  {failure['scenario_id']}: {failure['diagnosis']}")
            print(f"  {failure['scenario_id']}: {failure['patch_text']}")

        print("\nRETEST — only the failed scenarios, against v2")
        for result in report["tests"]:
            if result["version"] == "v2":
                _print_result("v2 retest", result)

    print()
    print(f"SCORE AFTER: {report['score_after_label']}")
    print(f"RESULT: {report['score_before_label']} -> {report['score_after_label']}")
    print()
    print("NARRATIVE (deterministic unless a wording key is configured)")
    print(report["narrative"])
    print()
    storage = report.get("storage") or {}
    print(f"RUN: {report['run_id']}")
    print(f"STORAGE: {storage.get('backend')} {storage.get('path', '')}".rstrip())
    print(f"N8N: {report['n8n_status']}")

    return 0 if (report["score_before"] == 1 and report["score_after"] == 5) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
