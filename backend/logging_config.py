"""JSON stdout logging (constitution Code & Naming Conventions).

Every log line is a JSON object carrying ``timestamp`` / ``level`` / ``module`` /
``message`` / ``trace_id``. The ``trace_id`` is propagated through a
``contextvars.ContextVar`` so it survives the hop from the async request handler
into the threadpool worker that runs ``agent_loop`` (Starlette's
``run_in_threadpool`` copies the current context).
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)


class _TraceFilter(logging.Filter):
    """Stamp each record with the current request's trace_id."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", None):
            record.trace_id = trace_id_var.get()  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def new_trace_id() -> str:
    """Bind a fresh trace_id to the current context and return it."""
    tid = uuid.uuid4().hex
    trace_id_var.set(tid)
    return tid


def get_trace_id() -> str | None:
    return trace_id_var.get()


def init_logging(level: int = logging.INFO) -> None:
    """Configure root + uvicorn loggers to emit JSON to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_TraceFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = [handler]
        lg.propagate = False
