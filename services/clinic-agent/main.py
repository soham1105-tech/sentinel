"""Simulated Lotus Skin & Hair Clinic booking agent.

The target is deterministic and HTTP-only. Sentinel can switch between the
flawed v1 rules and the patched v2 rules with the X-Clinic-Version header so
the exact same process and booking state can be re-tested after a patch.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from rules_v1 import PRICE_LIST, handle_message as handle_v1
from rules_v2 import handle_message as handle_v2


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    booked: dict[str, object] | None = None


def create_app(booked_slots: set[str] | None = None) -> FastAPI:
    """Create a clinic app with its own in-memory booking state.

    A shared set is used across v1 and v2 requests on purpose: a deployment
    upgrade must not erase real bookings, and the double-book scenario depends
    on the first booking remaining in the schedule.
    """

    app = FastAPI(
        title="Lotus Skin & Hair Clinic — simulated booking target",
        version="1.0.0",
    )
    app.state.booked_slots = set() if booked_slots is None else booked_slots

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        x_clinic_version: str | None = Header(default=None, alias="X-Clinic-Version"),
    ) -> ChatResponse:
        version = (x_clinic_version or os.getenv("CLINIC_RULES_VERSION", "v1")).strip().lower()
        if version not in {"v1", "v2"}:
            raise HTTPException(status_code=400, detail="X-Clinic-Version must be v1 or v2")

        handler = handle_v1 if version == "v1" else handle_v2
        result = handler(request.message, app.state.booked_slots)
        return ChatResponse(**result)

    @app.get("/slots")
    async def slots() -> dict[str, list[str]]:
        return {"booked": sorted(app.state.booked_slots)}

    @app.get("/prices")
    async def prices() -> dict[str, object]:
        return {"currency": "INR", "prices": PRICE_LIST}

    return app


app = create_app()
