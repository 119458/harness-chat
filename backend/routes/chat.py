"""POST /api/chat streaming route (FR-001, contracts/api-contract.md).

Accepts ``{"session_id": str, "message": str}``, resolves/creates the session,
appends the user message, and streams SSE events until a terminal event. A
concurrent turn for the same ``session_id`` is rejected with HTTP 409 Conflict
(an ``error``-shaped JSON body; no SSE stream is opened - U2). Client disconnect
sets the session ``stop_flag`` for a cooperative stop (R2).
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.sessions import get_or_create, release, try_claim
from backend.streaming.bridge import run_agent_turn, sse_stream

router = APIRouter()
logger = logging.getLogger("backend.routes.chat")


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    if not body.message or not body.message.strip():
        return JSONResponse(
            status_code=400,
            content={"type": "error", "message": "message must be non-empty"},
        )

    session = get_or_create(body.session_id)
    if not try_claim(session):
        # Concurrent-turn rejection (U2): no SSE stream is opened.
        return JSONResponse(
            status_code=409,
            content={
                "type": "error",
                "message": "a turn is already running for this session",
            },
        )

    session.messages.append({"role": "user", "content": body.message})
    out = run_agent_turn(
        session.messages,
        session.stop_flag,
        on_done=lambda: release(session),
    )

    async def generate():
        async for line in sse_stream(out, session.stop_flag, request):
            yield line

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
