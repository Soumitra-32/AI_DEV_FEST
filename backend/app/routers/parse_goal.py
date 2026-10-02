"""Goal-parsing endpoint: free text in, numbers out.

Thin by design: the parsing lives in the already-tested
:mod:`backend.genai.fallback.parse_goal` (Bangla digits, taka signs, lakh
grouping, thousand/lakh words). This router only validates the input shape
and returns what was found — never guessing a missing half.

Public (no token): parsing needs no user data and touches no database, so
there is nothing to protect. Invalid or empty input is a 422 from the schema,
never a 500.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.genai import fallback

from ..schemas import ParseGoalRequest, ParseGoalResponse

router = APIRouter(tags=["parse-goal"])


@router.post(
    "/parse-goal",
    response_model=ParseGoalResponse,
    summary="Extract goal amount and months from free text",
)
def parse_goal(body: ParseGoalRequest) -> ParseGoalResponse:
    """Return the goal/months found in the message (either may be missing)."""
    parsed = fallback.parse_goal(body.message)
    return ParseGoalResponse(
        goal_bdt=parsed.goal_bdt,
        months=parsed.months,
        is_complete=parsed.is_complete,
    )
