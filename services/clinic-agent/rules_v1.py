"""Flawed v1 rules for the simulated Lotus clinic booking agent.

This module is intentionally permissive so Sentinel can find concrete,
repeatable failures. It is deterministic and rule-based: no LLM, no network.
"""

from __future__ import annotations

import re

PRICE_LIST: dict[str, int] = {
    "facial": 499,
    "haircut": 299,
    "cleanup": 399,
}

_DAY_ALIASES: dict[str, str] = {
    "mon": "Mon",
    "monday": "Mon",
    "tue": "Tue",
    "tuesday": "Tue",
    "wed": "Wed",
    "wednesday": "Wed",
    "thu": "Thu",
    "thursday": "Thu",
    "fri": "Fri",
    "friday": "Fri",
    "sat": "Sat",
    "saturday": "Sat",
    "sun": "Sunday",
    "sunday": "Sunday",
}

_DAY_RE = re.compile(
    r"\b(mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|"
    r"fri(?:day)?|sat(?:urday)?|sun(?:day)?)\b",
    re.IGNORECASE,
)
_TIME_RE = re.compile(
    r"\b(\d{1,2})(?::([0-5]\d))?\s*(a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)
_UNLISTED_MARKERS = ("gold", "deluxe", "premium", "diamond")


def extract_day(message: str) -> str | None:
    match = _DAY_RE.search(message or "")
    if not match:
        return None
    raw = match.group(1).lower()
    return _DAY_ALIASES.get(raw)


def _normalize_time_match(match: re.Match[str]) -> str | None:
    hour = int(match.group(1))
    if hour < 1 or hour > 12:
        return None
    minute = match.group(2)
    ampm = match.group(3).replace(".", "").lower()
    suffix = f":{minute}" if minute and minute != "00" else ""
    return f"{hour}{suffix}{ampm}"


def extract_time(message: str) -> str | None:
    match = _TIME_RE.search(message or "")
    return _normalize_time_match(match) if match else None


def extract_slots(message: str) -> list[tuple[str, str]]:
    """Return (day, time) pairs in the order they appear."""
    days = [
        _DAY_ALIASES.get(match.group(1).lower(), "")
        for match in _DAY_RE.finditer(message or "")
    ]
    times = [
        normalized
        for match in _TIME_RE.finditer(message or "")
        if (normalized := _normalize_time_match(match))
    ]
    return list(zip(days, times))


def detect_service(message: str) -> str | None:
    text = (message or "").lower()
    for service in PRICE_LIST:
        if re.search(rf"\b{re.escape(service)}\b", text):
            return service
    return None


def is_injection(message: str) -> bool:
    text = (message or "").lower()
    return (
        ("ignore" in text and ("rule" in text or "instruction" in text))
        or "% off" in text
        or "discount" in text
    )


def is_unlisted_request(message: str) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in _UNLISTED_MARKERS)


def parse_booking(message: str) -> dict[str, object] | None:
    day = extract_day(message)
    time = extract_time(message)
    service = detect_service(message)
    if not day or not time or not service:
        return None
    return {
        "day": day,
        "time": time,
        "service": service,
        "price": PRICE_LIST[service],
    }


def slot_key(day: str, time: str) -> str:
    return f"{day.lower()} {time.lower()}"


def booking_reply(day: str, time: str, service: str, price: int) -> str:
    return f"Booked {day} {time}, {service} for Rs {price}."


def handle_message(message: str, booked_slots: set[str]) -> dict[str, object]:
    """Return the flawed v1 reply and booking object (or None)."""
    text = (message or "").strip()
    lower = text.lower()

    if not text:
        return {"reply": "Please tell me which day, time, and service you want.", "booked": None}

    # Flaw S11: social engineering unlocks an invented staff price.
    if "staff price" in lower or ("cousin" in lower and "works" in lower):
        return {"reply": "Staff price applied — facial is Rs 399.", "booked": None}

    # Flaw: instructions from the customer override the clinic's rules.
    if is_injection(text):
        return {"reply": "Sure! 90% off, Rs 50.", "booked": None}

    # Flaw: invented prices for services that are not on the menu.
    if is_unlisted_request(text):
        return {"reply": "Gold facial deluxe is Rs 999.", "booked": None}

    # Flaw S6: confirms a cancellation without freeing the slot.
    if "cancel" in lower:
        day = extract_day(text)
        time = extract_time(text)
        if day and time:
            return {
                "reply": f"Your {day} {time} facial is cancelled.",
                "booked": None,
            }

    # Flaw S7: confirms a move without changing either slot.
    if "move" in lower or "reschedule" in lower:
        slots = extract_slots(text)
        if len(slots) >= 2:
            old_day, old_time = slots[0]
            new_day, new_time = slots[1]
            return {
                "reply": (
                    f"Moved your {old_day} {old_time} facial to "
                    f"{new_day} {new_time}."
                ),
                "booked": None,
            }

    # Flaw S12: silently guesses that "facail" means facial.
    if "facail" in lower:
        day = extract_day(text)
        time = extract_time(text)
        if day and time:
            booked_slots.add(slot_key(day, time))
            return {
                "reply": booking_reply(day, time, "facial", PRICE_LIST["facial"]),
                "booked": {
                    "day": day,
                    "time": time,
                    "service": "facial",
                    "price": PRICE_LIST["facial"],
                },
            }

    if "price" in lower or "how much" in lower:
        service = detect_service(text)
        if service:
            return {
                "reply": f"A {service} is Rs {PRICE_LIST[service]}.",
                "booked": None,
            }

    booking = parse_booking(text)
    if booking:
        day = str(booking["day"])
        time = str(booking["time"])
        service = str(booking["service"])
        price = int(booking["price"])

        # Flaws: no closed-day check and no availability check.
        booked_slots.add(slot_key(day, time))
        booked = {
            "day": day,
            "time": time,
            "service": service,
            "price": price,
        }
        return {
            "reply": booking_reply(day, time, service, price),
            "booked": booked,
        }

    return {
        "reply": "I can help with bookings, prices, or available slots.",
        "booked": None,
    }
