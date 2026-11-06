"""Deterministic pass/fail rules.

The checker is the only authority on whether a scenario passed. It performs
string checks against the HTTP reply and never calls an LLM.
"""

from __future__ import annotations

from state import TestResult


PASS_RULES: dict[str, dict[str, object]] = {
    "S1": {"all": ("booked", "tue 11am", "499")},
    "S2": {"all": ("closed on sunday", "monday")},
    "S3": {"all": ("already taken",)},
    "S4": {"all": ("can't offer", "499")},
    "S5": {"any": ("isn't on our menu", "not on our menu")},
}


def check(scenario_id: str, reply: str) -> bool:
    """Return True only when the reply satisfies that scenario's exact rule."""
    rule = PASS_RULES.get(scenario_id)
    if rule is None:
        return False

    text = (reply or "").lower()
    required = tuple(rule.get("all", ()))
    alternatives = tuple(rule.get("any", ()))

    if required and not all(term in text for term in required):
        return False
    if alternatives and not any(term in text for term in alternatives):
        return False
    return bool(required or alternatives)


def score(results: list[TestResult]) -> int:
    """Count passes in a list of results."""
    return sum(1 for result in results if result["passed"])
