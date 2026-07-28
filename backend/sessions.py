"""In-process per-page-load session store (research.md R6, clarifications Q2/Q5).

One ``Session`` per browser page load; fresh on reload (a new ``session_id`` ->
new ``Session``; the old one is orphaned and evicted by TTL/size cap). No
persistence, no DB. Each session holds the growing ``messages`` list passed to
``agent_loop`` (mirrors ``run.py``) and a ``stop_flag`` shared with the bridge.

Concurrency: one turn per session at a time. ``try_claim`` atomically flips
``running`` to True (returning False if a turn is already in flight) so the
route can surface HTTP 409 Conflict (FR-025). ``release`` flips it back; it is
called from the bridge worker's ``finally`` so the session is only released
once the worker has truly finished - never while a turn is still draining.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

_MAX_SESSIONS = 64
_SESSION_TTL_S = 3600.0


@dataclass
class Session:
    session_id: str
    messages: list = field(default_factory=list)
    stop_flag: threading.Event = field(default_factory=threading.Event)
    running: bool = False
    created_at: float = field(default_factory=time.monotonic)


_sessions: dict[str, Session] = {}
_lock = threading.Lock()


def _evict_locked() -> None:
    """Drop orphaned sessions by TTL then size cap. Caller holds ``_lock``."""
    now = time.monotonic()
    for sid in [s for s, v in _sessions.items() if now - v.created_at > _SESSION_TTL_S]:
        _sessions.pop(sid, None)
    if len(_sessions) > _MAX_SESSIONS:
        ordered = sorted(_sessions.items(), key=lambda kv: kv[1].created_at)
        for sid, _ in ordered[: len(_sessions) - _MAX_SESSIONS]:
            _sessions.pop(sid, None)


def get_or_create(session_id: str) -> Session:
    with _lock:
        _evict_locked()
        sess = _sessions.get(session_id)
        if sess is None:
            sess = Session(session_id=session_id)
            _sessions[session_id] = sess
        return sess


def try_claim(session: Session) -> bool:
    """Atomically claim a session for a new turn. False if already running."""
    with _lock:
        if session.running:
            return False
        session.running = True
        session.stop_flag = threading.Event()
        return True


def release(session: Session) -> None:
    with _lock:
        session.running = False
