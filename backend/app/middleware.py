"""PII-free request logging (monitoring).

The plan's monitoring row asks for "request logs (no PII)". This middleware logs
exactly the shape of a request the metrics page needs -- method, path, status,
duration -- and nothing that could identify a person:

* the **query string is never logged** (a ``?message=`` would carry free text);
* request/response **headers and bodies are never logged** (the demo token and
  any free text live there);
* the authenticated user is never recorded.

Each line is appended as JSONL to :attr:`Settings.request_log_file` beside
``metrics.json``, so ``GET /metrics`` can summarise traffic without a second
datastore. Writing is best-effort: a read-only artifact mount degrades the log,
never the request.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

logger = logging.getLogger("shonchoy.requests")


def _append(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON line, swallowing any I/O error on purpose."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:  # pragma: no cover - read-only mount
        logger.debug("request log not writable at %s", path)


def add_request_logging(app: FastAPI, log_path: Path) -> None:
    """Install the PII-free request logger on ``app``."""

    @app.middleware("http")
    async def _log_request(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        record = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "method": request.method,
            "path": request.url.path,  # never the query string
            "status": int(response.status_code),
            "duration_ms": elapsed_ms,
        }
        logger.info(
            "request method=%s path=%s status=%s ms=%s",
            record["method"], record["path"], record["status"], record["duration_ms"],
        )
        _append(log_path, record)
        return response
