"""Optional wording layer: Gemini first, Groq fallback.

The LLM never decides pass/fail and never computes the score. It only rewrites
an already-measured, structured report. With no keys, a deterministic local
narrative is returned so the CLI and tests always work.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"


def fallback_report(facts: dict[str, Any]) -> str:
    before = facts.get("score_before_label", "unknown")
    after = facts.get("score_after_label", "unknown")
    failure_ids = ", ".join(
        failure.get("scenario_id", "?") for failure in facts.get("failures", [])
    ) or "none"
    patch_count = len(facts.get("patches", []))
    return (
        f"Measured reliability moved from {before} to {after}. "
        f"Failures detected before patching: {failure_ids}. "
        f"Sentinel applied {patch_count} guardrail patch(es) and re-ran only the "
        "failed scenarios against v2. Every verdict came from deterministic "
        "string checks, and the transcripts above are the evidence."
    )


def _prompt(facts: dict[str, Any]) -> str:
    compact = json.dumps(facts, ensure_ascii=False, indent=2, default=str)
    return (
        "You are a precise technical writer for an AI reliability report. "
        "Rewrite the measured facts below as a concise engineering summary "
        "(maximum 130 words). Do not invent users, tests, causes, or results. "
        "Do not change any score or verdict. Do not decide pass/fail. "
        "Use only the facts provided.\n\n"
        f"MEASURED FACTS:\n{compact}"
    )


def _gemini(prompt: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = (getattr(response, "text", "") or "").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 - wording must never break a run
        logger.warning("Gemini wording failed; falling back: %s", exc)
        return None


def _groq(prompt: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Rewrite measured facts only. Never decide pass/fail.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=220,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 - wording must never break a run
        logger.warning("Groq wording failed; using local fallback: %s", exc)
        return None


def word_report(facts: dict[str, Any]) -> tuple[str, str]:
    """Return (narrative, source). Source is deterministic when no key is set."""
    prompt = _prompt(facts)

    text = _gemini(prompt)
    if text:
        return text, f"gemini:{GEMINI_MODEL}"

    text = _groq(prompt)
    if text:
        return text, f"groq:{GROQ_MODEL}"

    return fallback_report(facts), "deterministic"
