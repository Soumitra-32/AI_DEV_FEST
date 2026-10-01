"""Service health and identity endpoints.

``/health`` is public and defensive (it reports "degraded" instead of failing, so
Render/Vercel probes never see a 500). ``/me`` is authenticated and exists to
prove the token -> ``user_id`` path works end to end.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import Settings, get_settings
from ..deps import Connection, CurrentUser
from ..schemas import DatabaseInfo, HealthResponse, IdentityResponse

router = APIRouter(tags=["health"])


def _count(connection: sqlite3.Connection, table: str) -> int:
    try:
        row = connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
    except sqlite3.Error:
        return 0
    return int(row["total"]) if row else 0


def _generation_meta(connection: sqlite3.Connection) -> Dict[str, str]:
    try:
        rows = connection.execute("SELECT key, value FROM generation_meta").fetchall()
    except sqlite3.Error:
        return {}
    return {str(row["key"]): str(row["value"]) for row in rows}


@router.get("/health", response_model=HealthResponse, summary="Service and dataset health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Public probe: reports the dataset size and which feature flags are on."""
    database = DatabaseInfo(available=False, path=str(settings.db_path))
    overall = "degraded"

    if settings.db_path.exists():
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"file:{settings.db_path.as_posix()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            meta = _generation_meta(connection)
            database = DatabaseInfo(
                available=True,
                path=str(settings.db_path),
                users=_count(connection, "users"),
                transactions=_count(connection, "transactions"),
                generated_at=meta.get("created_at"),
            )
            overall = "ok"
        except sqlite3.Error:
            overall = "degraded"
        finally:
            if connection is not None:
                connection.close()

    return HealthResponse(
        status=overall,
        version=settings.api_version,
        database=database,
        features=settings.feature_flags(),
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/me", response_model=IdentityResponse, summary="Identity behind the demo token")
def me(
    user_id: CurrentUser,
    connection: Connection,
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityResponse:
    """Returns the user the token maps to — never a user id from the request."""
    row = connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user {user_id} is not in the dataset; run backend/scripts/generate_data.py",
        )

    is_demo_user = user_id == settings.demo_user_id
    return IdentityResponse(
        user_id=str(row["user_id"]),
        name_en=settings.demo_user_name_en if is_demo_user else "",
        name_bn=settings.demo_user_name_bn if is_demo_user else "",
        persona=row["persona"],
        district=row["district"],
        income_band=row["income_band"],
        language_pref=row["language_pref"],
        cohort=str(row["cohort"]),
        is_demo_user=is_demo_user,
    )

