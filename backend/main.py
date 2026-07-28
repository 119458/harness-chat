"""FastAPI app: dev CORS, JSON logging init, trace_id + exception middleware.

The streaming ``POST /api/chat`` route is registered in
``backend/routes/chat.py`` (T013). In-stream failures there are converted to an
SSE ``type:"error"`` event inside the bridge (R3); the middleware here is the
backstop for anything that escapes before the stream starts, and it logs every
uncaught exception as a JSON line carrying ``trace_id``.
"""

from __future__ import annotations

import logging

# Load .env (BASE_URL/API_KEY/MODEL/WORKDIR) BEFORE importing the agent chain:
# loop/loop.py -> tool/tool.py reads WORKDIR / error.py reads MODEL at import
# time. This reads the same config run.py uses; no bypass (constitution §运行时配置).
from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.logging_config import init_logging, new_trace_id
from backend.routes.chat import router as chat_router

init_logging()
logger = logging.getLogger("backend.main")

app = FastAPI(title="Harness Chat", docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.middleware("http")
async def trace_and_error_middleware(request: Request, call_next):
    """Bind a per-request trace_id; convert uncaught exceptions to error JSON."""
    new_trace_id()
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - backstop, logged with trace_id
        logger.exception("unhandled request error")
        return JSONResponse(
            status_code=500,
            content={"type": "error", "message": "internal server error"},
        )


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
