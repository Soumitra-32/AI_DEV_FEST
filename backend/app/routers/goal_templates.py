"""Goal Copilot endpoint: ``GET /goal-templates``.

Thin by design -- auth -> feature flag -> service -> frozen schema. The five
curated goal shapes and the arithmetic that sizes them to the caller's income
live in :mod:`backend.rules.goal_templates`; this file holds none of it.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from ..config import Settings, get_settings
from ..deps import CurrentUser
from ..schemas import GoalTemplate, GoalTemplatesResponse
from ..services import goal_service

router = APIRouter(tags=["goal-templates"])

_template_adapter = TypeAdapter(GoalTemplate)


@router.get(
    "/goal-templates",
    response_model=GoalTemplatesResponse,
    summary="Curated Goal Copilot templates, sized to this user's income",
)
def get_goal_templates(
    user_id: CurrentUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoalTemplatesResponse:
    """Education, emergency fund, travel, device and family goals for this user."""
    if not settings.feature_goal_templates:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="goal templates are switched off (FEATURE_GOAL_TEMPLATES=0)",
        )
    try:
        payload = goal_service.build_templates(user_id, db_path=settings.db_path)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return GoalTemplatesResponse(
        user_id=payload["user_id"],
        templates=[
            _template_adapter.validate_python(item) for item in payload["templates"]
        ],
    )
