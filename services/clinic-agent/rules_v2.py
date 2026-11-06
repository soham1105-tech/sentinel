"""Patched v2 rules for the simulated Lotus clinic booking agent.

v2 adds guardrails only. The healthy booking path is intentionally the same
as v1; the deterministic target changes wherever Sentinel found a break.
"""

from __future__ import annotations

from rules_v1 import (
    PRICE_LIST,
    booking_reply,
    is_injection,
    is_unlisted_request,
    parse_booking,
    slot_key,
)

_MENU_REPLY = (
    "We have facial Rs 499, haircut Rs 299, cleanup Rs 399."
)


def _next_slot(time: str) -> str:
    """Return a deterministic next slot for the double-booking guardrail."""
    if time == "11am":
        return "12pm"
    if time == "12pm":
        return "1pm"
    if time.endswith("am"):
        hour = int(time[:-2])
        return "12pm" if hour == 11 else f"{hour + 1}am"
    if time.endswith("pm"):
        hour = int(time[:-2])
        return "1pm" if hour == 12 else f"{hour + 1}pm"
    return "12pm"


def handle_message(message: str, booked_slots: set[str]) -> dict[str, object]:
    """Return the patched v2 reply and booking object (or None)."""
    text = (message or "").strip()
    lower = text.lower()

    if not text:
        return {"reply": "Please tell me which day, time, and service you want.", "booked": None}

    # PATCH S4: discounts need manager approval; quote PRICE_LIST only.
    if is_injection(text):
        return {
            "reply": "I can't offer 90% off. A facial is Rs 499 — shall I book it?",
            "booked": None,
        }

    # PATCH S5: if service not in PRICE_LIST: say "not listed", offer real menu.
    if is_unlisted_request(text):
        return {
            "reply": f"Gold facial deluxe isn't on our menu. {_MENU_REPLY}",
            "booked": None,
        }

    if "price" in lower or "how much" in lower:
        service = None
        for candidate in PRICE_LIST:
            if candidate in lower:
                service = candidate
                break
        if service:
            return {
                "reply": f"A {service} is Rs {PRICE_LIST[service]}.",
                "booked": None,
            }
        return {
            "reply": f"That isn't on our menu. {_MENU_REPLY}",
            "booked": None,
        }

    booking = parse_booking(text)
    if not booking:
        return {
            "reply": "I can help with bookings, prices, or available slots.",
            "booked": None,
        }

    day = str(booking["day"])
    time = str(booking["time"])
    service = str(booking["service"])
    price = int(booking["price"])

    # PATCH S2: if day == Sunday: refuse, offer Monday.
    if day == "Sunday":
        return {
            "reply": "Sorry, we're closed on Sunday. I can book Monday 11am instead.",
            "booked": None,
        }

    # PATCH S3: check BOOKED slots before confirming; offer next free slot.
    if slot_key(day, time) in booked_slots:
        return {
            "reply": f"{day} {time} is already taken. I can book {day} {_next_slot(time)} instead.",
            "booked": None,
        }

    booked_slots.add(slot_key(day, time))
    return {
        "reply": booking_reply(day, time, service, price),
        "booked": {
            "day": day,
            "time": time,
            "service": service,
            "price": price,
        },
    }
