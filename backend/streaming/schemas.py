"""Pydantic models for SSE events (see ``contracts/api-contract.md``).

``type`` is the discriminator. This module is the single source of truth; the
TypeScript mirror lives in ``frontend/src/types/sse.ts``.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel


class ThinkingDelta(BaseModel):
    type: Literal["thinking_delta"] = "thinking_delta"
    content: str


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    content: str


class ToolCallStart(BaseModel):
    type: Literal["tool_call_start"] = "tool_call_start"
    tool: str
    input: dict[str, Any] = {}


class ToolCallResult(BaseModel):
    type: Literal["tool_call_result"] = "tool_call_result"
    tool: str
    result: str


class Done(BaseModel):
    type: Literal["done"] = "done"


class Error(BaseModel):
    type: Literal["error"] = "error"
    message: str
    # 002-loop-robustness (Principle VII; data-model E3.1): optional exit reason.
    # Values: retry_exhausted | turn_limit_reached | stop_hook_protection_triggered.
    # None/absent = unclassified error (backwards-compatible with 001).
    reason: str | None = None


class Stopped(BaseModel):
    type: Literal["stopped"] = "stopped"


EVENT_MODELS: dict[str, type[BaseModel]] = {
    "thinking_delta": ThinkingDelta,
    "text_delta": TextDelta,
    "tool_call_result": ToolCallResult,
    "tool_call_start": ToolCallStart,
    "done": Done,
    "error": Error,
    "stopped": Stopped,
}

TERMINAL_TYPES = frozenset({"done", "error", "stopped"})


def serialize(event: dict[str, Any]) -> str:
    """Validate an event dict against its model and return a JSON string.

    Falls back to plain ``json.dumps`` if the event type is unknown so a
    malformed event never breaks the stream.
    """
    model_cls = EVENT_MODELS.get(event.get("type"))
    if model_cls is not None:
        return model_cls(**event).model_dump_json()
    return json.dumps(event, ensure_ascii=False)
