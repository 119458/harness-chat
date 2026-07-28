"""Sync<->async streaming bridge (research.md R1/R2/R3/R7).

Runs the synchronous ``agent_loop`` in a daemon thread; the ``on_event`` hook
pushes events into a thread-safe queue which an async generator drains and
emits as SSE lines.

Guarantees:
  * Exactly one terminal event (done/error/stopped) is pushed before the
    sentinel (R3) - the client never stalls waiting for end-of-stream.
  * Stop is cooperative: ``on_event`` raises ``StopRequested`` (a
    ``BaseException``) at a safe boundary, bypassing ``loop/loop.py``'s
    unchanged ``except Exception`` (R2).
  * No buffering: every delta is ``queue.put`` immediately inside the stream
    loop (R7).
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import Any, AsyncGenerator, Callable

from backend.streaming.schemas import TERMINAL_TYPES, serialize
from loop.loop import agent_loop

logger = logging.getLogger("backend.streaming.bridge")

# Sentinel pushed last to signal the producer is finished.
_SENTINEL: Any = object()


class StopRequested(BaseException):
    """Cooperative stop signal (R2).

    Subclasses ``BaseException`` (not ``Exception``) so it bypasses
    ``loop/loop.py``'s unchanged ``except Exception`` and propagates out of
    ``agent_loop`` to this bridge, which emits a ``stopped`` terminal event.
    """


def _safe_message(exc: BaseException) -> str:
    name = type(exc).__name__
    detail = str(exc).strip()[:300]
    return f"{name}: {detail}" if detail else name


def run_agent_turn(
    messages: list,
    stop_flag: threading.Event,
    on_done: Callable[[], None] | None = None,
) -> "queue.Queue[Any]":
    """Run ``agent_loop`` in a daemon thread; return a queue of SSE events.

    The queue receives incremental events as produced and exactly one terminal
    event before the sentinel. ``on_done`` (if provided) is called from the
    worker's ``finally`` once the turn is truly finished - use it to release the
    session so a new turn cannot start while the worker is still draining.
    """
    out: "queue.Queue[Any]" = queue.Queue()
    state = {"terminal": False}

    def on_event(event: dict) -> None:
        # Terminal events are always emitted (never blocked by a stop race).
        if event.get("type") in TERMINAL_TYPES:
            out.put(event)
            state["terminal"] = True
            return
        # Cooperative stop check at a safe boundary: on_event is only called
        # between deltas / between tool dispatches, never mid-execute_tool (R2).
        if stop_flag.is_set():
            raise StopRequested()
        out.put(event)

    def worker() -> None:
        try:
            agent_loop(messages, on_event=on_event)
        except StopRequested:
            out.put({"type": "stopped"})
            state["terminal"] = True
        except Exception as exc:
            logger.exception("agent_loop crashed")
            out.put({"type": "error", "message": _safe_message(exc)})
            state["terminal"] = True
        finally:
            if not state["terminal"]:
                # R3: abnormal return with no prior terminal event.
                out.put(
                    {
                        "type": "error",
                        "message": "agent loop ended without a terminal event",
                    }
                )
            out.put(_SENTINEL)
            if on_done is not None:
                try:
                    on_done()
                except Exception:  # noqa: BLE001 - never break the worker exit
                    logger.exception("on_done callback failed")

    threading.Thread(target=worker, daemon=True).start()
    return out


async def sse_stream(
    out: "queue.Queue[Any]",
    stop_flag: threading.Event,
    request: Any,
) -> AsyncGenerator[str, None]:
    """Async generator yielding ``data: {json}\\n\\n`` SSE lines.

    Drains the queue until a terminal event or client disconnect. On disconnect
    (proactive ``is_disconnected`` check OR uvicorn cancelling the generator
    with ``GeneratorExit``/``CancelledError``) the ``finally`` sets
    ``stop_flag`` so the worker stops at the next safe boundary (R2); the worker
    itself releases the session via ``on_done``.
    """
    try:
        while True:
            try:
                item = await asyncio.to_thread(out.get, True, 0.5)
            except queue.Empty:
                if await request.is_disconnected():
                    return
                continue
            if item is _SENTINEL:
                return
            yield f"data: {serialize(item)}\n\n"
            if item.get("type") in TERMINAL_TYPES:
                return
            if await request.is_disconnected():
                return
    finally:
        # Any exit path (terminal, proactive disconnect, or uvicorn cancelling
        # the generator on client disconnect) signals stop. No-op if the worker
        # already finished; otherwise it stops at the next on_event (R2).
        stop_flag.set()
