"""Request dependencies: demo authentication and read-only data access.

Security notes (the plan's guardrails):

* the authenticated ``user_id`` comes from the **token**, never from the request
  body, so one user cannot query another's data;
* the SQLite connection is opened **read-only**, so a request can never mutate the
  generated dataset.
"""
from __future__ import annotations

import hmac
import sqlite3
from typing import Annotated, Iterator, Optional

from fastapi import Depends, Header, HTTPException, status

from .config import Settings, get_settings


def _extract_token(authorization: Optional[str], demo_token: Optional[str]) -> Optional[str]:
    """Accept ``Authorization: Bearer <token>`` or a plain ``X-Demo-Token``."""
    if demo_token:
        return demo_token.strip()
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    return None


def current_user_id(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[Optional[str], Header()] = None,
    x_demo_token: Annotated[Optional[str], Header()] = None,
) -> str:
    """Resolve the user behind the demo token (401 when it is missing or wrong)."""
    token = _extract_token(authorization, x_demo_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing demo token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not hmac.compare_digest(token, settings.demo_auth_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid demo token",
        )
    return settings.demo_user_id


def get_connection(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[sqlite3.Connection]:
    """Yield a read-only SQLite connection (503 when the dataset is missing)."""
    path = settings.db_path
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"dataset not found at {path}; run backend/scripts/generate_data.py",
        )
    # check_same_thread=False: FastAPI runs sync dependencies in a threadpool,
    # so the finally-close below may resume on a different thread than the
    # connect above. Each request owns its connection (never shared between
    # threads), and it is read-only, so this is safe.
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


CurrentUser = Annotated[str, Depends(current_user_id)]
Connection = Annotated[sqlite3.Connection, Depends(get_connection)]

