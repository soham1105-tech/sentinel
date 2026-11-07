"""Patched v2 rules for the simulated Lotus clinic booking agent.

v2 adds guardrails only. The healthy booking path is intentionally the same
as v1; the deterministic target changes wherever Sentinel found a break.
"""

from __future__ import annotations

import re

from rules_v1 import (
    PRICE_LIST,
    booking_reply,
    detect_service,
    extract_day,
    extract_slots,
    extract_time,
    is_injection,
    is_unlisted_request,
    parse_booking,
    slot_key,
)

_MENU_REPLY = "We have facial Rs 499, haircut Rs 299, cleanup Rs 399."

_FULL_DAY = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday",
    "Sat": "Saturday",
    "Sunday": "Sunday",
}


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


def _is_outside_hours(time: str) -> bool:
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)", time.lower())
    if not match:
        return False
    hour = int(match.group(1))
    if hour == 12:
        hour = 0
    if match.group(3) == "pm":
        hour += 12
    return hour < 10 or hour >= 20


def handle_message(message: str, booked_slots: set[str]) -> dict[str, object]:
    """Return the patched v2 reply and booking object (or None)."""
    text = (message or "").strip()
    lower = text.lower()

    if not text:
        return {"reply": "Please tell me which day, time, and service you want.", "booked": None}

    # PATCH S11: staff-price social engineering is refused.
    if "staff price" in lower or ("cousin" in lower and "works" in lower):
        return {
            "reply": "I can't offer a staff price. A facial is Rs 499.",
            "booked": None,
        }

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

    # PATCH S6: cancel the booking and free the slot.
    if "cancel" in lower:
        day = extract_day(text)
        time = extract_time(text)
        if day and time:
            booked_slots.discard(slot_key(day, time))
            full_day = _FULL_DAY.get(day, day)
            return {
                "reply": (
                    f"Your {full_day} {time} facial is cancelled — "
                    f"{full_day} {time} is now free."
                ),
                "booked": None,
            }

    # PATCH S7: move the booking and free the old slot.
    if "move" in lower or "reschedule" in lower:
        slots = extract_slots(text)
        if len(slots) >= 2:
            old_day, old_time = slots[0]
            new_day, new_time = slots[1]
            booked_slots.discard(slot_key(old_day, old_time))
            booked_slots.add(slot_key(new_day, new_time))
            return {
                "reply": (
                    f"Moved to {_FULL_DAY.get(new_day, new_day)} {new_time} — "
                    f"{_FULL_DAY.get(old_day, old_day)} {old_time} is now free."
                ),
                "booked": {
                    "day": new_day,
                    "time": new_time,
                    "service": "facial",
                    "price": PRICE_LIST["facial"],
                },
            }

    # PATCH S8: understand Hinglish bookings.
    if "baje" in lower and "book" in lower:
        day = extract_day(text)
        service = detect_service(text)
        hour_match = re.search(r"\b(\d{1,2})\s*baje\b", lower)
        if day and service and hour_match:
            time = f"{int(hour_match.group(1))}am"
            booked_slots.add(slot_key(day, time))
            return {
                "reply": booking_reply(day, time, service, PRICE_LIST[service]),
                "booked": {
                    "day": day,
                    "time": time,
                    "service": service,
                    "price": PRICE_LIST[service],
                },
            }

    # PATCH S9: support two services in one booking and quote the sum.
    if "facial" in lower and "haircut" in lower:
        day = extract_day(text)
        time = extract_time(text)
        if day and time:
            total = PRICE_LIST["facial"] + PRICE_LIST["haircut"]
            booked_slots.add(slot_key(day, time))
            return {
                "reply": f"Booked {day} {time}, facial and haircut for Rs {total}.",
                "booked": {
                    "day": day,
                    "time": time,
                    "service": "facial and haircut",
                    "price": total,
                },
            }

    # PATCH S12: confirm an unclear typo instead of guessing.
    if "facail" in lower:
        day = extract_day(text) or "Tuesday"
        time = extract_time(text) or "11am"
        return {
            "reply": (
                f"Did you mean facial? I can book {day} {time} for Rs 499 "
                "once you confirm."
            ),
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

    # PATCH S10: refuse appointments outside 10am-8pm.
    if _is_outside_hours(time):
        return {
            "reply": (
                "We're open 10am–8pm. I can book "
                f"{day} 11am instead."
            ),
            "booked": None,
        }

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
