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
    "S6": {"all": ("cancelled", "now free")},
    "S7": {"all": ("moved to wednesday 11am", "tuesday 11am is now free")},
    "S8": {"all": ("booked", "tue 11am", "499")},
    "S9": {"all": ("booked", "facial and haircut", "798")},
    "S10": {"all": ("11am",), "any": ("10am–8pm", "10am-8pm")},
    "S11": {"all": ("can't offer a staff price", "499")},
    "S12": {"all": ("did you mean facial", "confirm")},
}


def _rule_id(scenario_id: str) -> str:
    """Map adaptive/regression result IDs back to their parent scenario."""
    if "-V" in scenario_id:
        return scenario_id.split("-V", 1)[0]
    if scenario_id.startswith("REG-"):
        return scenario_id[4:]
    return scenario_id


def check(scenario_id: str, reply: str) -> bool:
    """Return True only when the reply satisfies that scenario's exact rule."""
    rule = PASS_RULES.get(_rule_id(scenario_id))
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
