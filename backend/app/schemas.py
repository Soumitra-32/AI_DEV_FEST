"""Request and response contracts for every endpoint.

These schemas are written **before** the services that fill them (the plan's rule:
"schemas before services, rules before LLM"), so the frontend can be built against
a frozen contract. Phase 2 implements ``/health`` and ``/me``; the remaining
routers return these same shapes as they come online.

Every user-facing number carries a ``provenance`` block that separates
**Prediction / Assumption / Explanation**, so the UI can always show what we
think, what we assumed, and why.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["rule", "model", "template", "llm"]
Language = Literal["bn", "en"]
ActionType = Literal["reduce", "delay", "switch", "do_nothing"]
ConsistencyBand = Literal["Building", "Steady", "Strong"]
Intent = Literal[
    "explain_transactions",
    "forecast",
    "savings_plan",
    "fees",
    "consistency",
    "tips",
    "health_coach",
    "anomalies",
    "tradeoffs",
    "unknown",
]
Dimension = Literal["persona", "district", "income_band"]


class StrictModel(BaseModel):
    """Response base that **rejects unknown fields** instead of ignoring them.

    Used where silently accepting an extra field would be a safety problem — e.g.
    a numeric credit score must not be able to slip into the consistency-signal
    contract.
    """

    model_config = ConfigDict(extra="forbid")


class Provenance(BaseModel):
    """The Prediction / Assumption / Explanation block shown on every card."""

    prediction: str = Field(description="What we think will happen")
    assumption: str = Field(description="What we assumed to get there")
    explanation: str = Field(description="Why, in plain language")
    source: SourceType = Field(default="rule", description="rule | model | template | llm")


class ErrorResponse(BaseModel):
    """Uniform error body."""

    detail: str


# ---------------------------------------------------------------------------
# health and identity
# ---------------------------------------------------------------------------
class DatabaseInfo(BaseModel):
    """What the API can see of the generated dataset."""

    available: bool
    path: str
    users: int = 0
    transactions: int = 0
    generated_at: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: DatabaseInfo
    features: Dict[str, bool]
    checked_at: datetime


class IdentityResponse(BaseModel):
    """Who the presented token belongs to (proves auth works end to end)."""

    user_id: str
    name_en: str = ""
    name_bn: str = ""
    persona: Optional[str] = None
    district: Optional[str] = None
    income_band: Optional[str] = None
    language_pref: Language = "bn"
    cohort: str = "demo"
    is_demo_user: bool = True


# ---------------------------------------------------------------------------
# POST /forecast
# ---------------------------------------------------------------------------
class ForecastRequest(BaseModel):
    horizon_days: int = Field(default=14, ge=1, le=60)
    include_pressure_days: bool = True
    as_of: Optional[date] = Field(
        default=None,
        description="ISO date placing the window: only history on or before "
        "this date is used, so the outlook can cover month-end days 28-31",
    )


class DayForecast(BaseModel):
    date: date
    predicted_inflow_bdt: float
    predicted_outflow_bdt: float
    predicted_net_bdt: float
    predicted_balance_bdt: Optional[float] = Field(
        default=None, description="Expected wallet balance at the end of the day"
    )
    is_pressure_day: bool = False
    pressure_reason: Optional[str] = None


class Driver(BaseModel):
    """A top feature behind a prediction (SHAP or model importance)."""

    feature: str
    direction: Literal["increases", "decreases"]
    impact_bdt: float
    detail: str


class ForecastMetrics(BaseModel):
    model_name: str
    mae_bdt: float
    rmse_bdt: float
    baseline_name: str
    baseline_mae_bdt: float
    improvement_pct: float


class ForecastResponse(BaseModel):
    user_id: str
    horizon_days: int
    generated_at: datetime
    generated_from: Optional[date] = Field(
        default=None, description="Last day of real history the forecast was made from"
    )
    net_source: Literal["model", "difference", "anchor"] = Field(
        default="model",
        description=(
            "Whether predicted net came from the dedicated net model, from "
            "inflow minus outflow, or from the trailing-28-day anchor level "
            "('anchor': the model disagreed with the user's own flows beyond "
            "tolerance, so its level was set aside — see the assumption)."
        ),
    )
    days: List[DayForecast] = Field(default_factory=list)
    pressure_days: List[date] = Field(default_factory=list)
    drivers: List[Driver] = Field(default_factory=list)
    metrics: Optional[ForecastMetrics] = None
    provenance: Provenance


# ---------------------------------------------------------------------------
# POST /savings-plan
# ---------------------------------------------------------------------------
class SavingsPlanRequest(BaseModel):
    goal_bdt: float = Field(gt=0, le=10_000_000, description="Target amount in taka")
    months: int = Field(ge=1, le=36)
    goal_label: Optional[str] = Field(default=None, description="Optional goal text from the user")


class TradeOffOption(BaseModel):
    action: ActionType
    title: str
    description: str
    months: Optional[int] = None
    target_bdt: Optional[float] = None
    monthly_amount_bdt: Optional[float] = None
    monthly_effect_bdt: Optional[float] = None


class DoNothingOutcome(BaseModel):
    description: str
    estimated_cost_bdt: float
    horizon_months: int


class SavingsPlanResponse(BaseModel):
    user_id: str
    goal_bdt: float
    months: int
    feasible: bool
    required_monthly_bdt: float
    forecasted_surplus_bdt: float
    safety_buffer_bdt: float
    feasible_monthly_bdt: float
    arithmetic: List[str] = Field(
        default_factory=list, description="Step-by-step rule trace of the solver"
    )
    trade_offs: List[TradeOffOption] = Field(default_factory=list)
    do_nothing: DoNothingOutcome
    pressure_days: List[date] = Field(
        default_factory=list, description="Days the plan has to survive (from the forecast)"
    )
    provenance: Provenance


# ---------------------------------------------------------------------------
# POST /parse-goal  (voice/text -> numbers for the savings form)
# ---------------------------------------------------------------------------
class ParseGoalRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500, description="Free Bangla/English text")


class ParseGoalResponse(BaseModel):
    goal_bdt: Optional[float] = Field(default=None, description="Parsed amount, if present")
    months: Optional[int] = Field(default=None, description="Parsed horizon, if present")
    is_complete: bool = Field(description="True when both halves are present")


# ---------------------------------------------------------------------------
# POST /anomalies  (Spending Companion)
# ---------------------------------------------------------------------------
class AnomalyRequest(BaseModel):
    window_days: int = Field(default=30, ge=7, le=180)
    limit: int = Field(default=20, ge=1, le=100)


class AnomalyItem(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount_bdt: float
    channel: str
    category: str
    anomaly_type: Optional[str] = Field(default=None, description="Ground-truth type when known")
    score: Optional[float] = Field(default=None, description="Model score, higher = odder")
    reason: str = Field(description="Which feature deviated from this user's own norm")
    suggested_action: ActionType = "reduce"
    suggested_channel: Optional[str] = None


class FeeSwitchSuggestion(BaseModel):
    cash_out_count: int
    cash_out_volume_bdt: float
    fee_paid_bdt: float
    alternative_channel: str
    alternative_fee_bdt: float
    potential_saving_bdt: float
    adoption_range: str = Field(
        default="20%-50%", description="Assumed adoption range, not a measured result"
    )


class AnomalyResponse(BaseModel):
    user_id: str
    window_days: int
    items: List[AnomalyItem] = Field(default_factory=list)
    fee_switch: Optional[FeeSwitchSuggestion] = None
    provenance: Provenance


# ---------------------------------------------------------------------------
# POST /credit-readiness  (Financial Consistency Signal)
# ---------------------------------------------------------------------------
class SignalFactor(BaseModel):
    feature: str
    direction: Literal["improves", "weakens"]
    magnitude: float
    plain_language: str


class ShapFeature(BaseModel):
    """One feature's exact contribution to this user's log-odds.

    Signed, unlike :class:`SignalFactor.magnitude`, which is an absolute size
    stripped of direction: a positive value pushes towards "stable", a negative
    one pushes away. :mod:`backend.ml.signal` produces these from
    ``shap.LinearExplainer``, which is exact for a linear model.
    """

    feature: str
    contribution: float = Field(description="Signed SHAP value in log-odds")
    direction: Literal["improves", "weakens"]
    rank: int = Field(ge=1, description="1 = the largest absolute contribution")


class ShapExplanation(BaseModel):
    """The model's reasoning for the band, in the units the model actually used.

    ``base_value`` is the model's output before any of this user's features are
    applied, so ``base_value + sum(contribution)`` reconstructs the log-odds that
    produced the band. Exposing the whole ranked list (not just the three
    summarised in ``factors``) is what makes the band auditable: a reader can
    check the arithmetic instead of taking the top three on trust.

    Absent (``None``) when the rule band answered, because a rule has no SHAP
    values -- an empty contribution list would look like "nothing mattered".
    """

    method: str = Field(description="How the values were computed, e.g. shap.LinearExplainer")
    base_value: float
    log_odds: float = Field(description="The model's log-odds for this user")
    band_cutoffs: Dict[str, float] = Field(
        default_factory=dict, description="Probability at which each band starts"
    )
    features: List[ShapFeature] = Field(default_factory=list)


class ConsistencySignalResponse(StrictModel):
    """A band, never a score, and never a lending decision."""

    user_id: str
    band: ConsistencyBand
    factors: List[SignalFactor] = Field(default_factory=list, max_length=3)
    improvements: List[str] = Field(default_factory=list)
    not_a_decision: bool = True
    banner_en: str = "This is not a loan eligibility decision."
    banner_bn: str = "এটি ঋণ পাওয়ার সিদ্ধান্ত নয়।"
    auc: Optional[float] = Field(default=None, description="Held-out AUC of the demo model")
    shap: Optional[ShapExplanation] = Field(
        default=None,
        description=(
            "Exact per-feature contributions behind the band; null when the rule "
            "band answered, since a rule has no SHAP values"
        ),
    )
    provenance: Provenance


# ---------------------------------------------------------------------------
# POST /chat-explain
# ---------------------------------------------------------------------------
class ExplainRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    language: Language = "bn"
    intent: Optional[Intent] = Field(
        default=None, description="Optional client hint; the server always re-classifies"
    )


class ExplainResponse(BaseModel):
    intent: Intent
    answer_bn: str
    answer_en: str
    bullets_bn: List[str] = Field(default_factory=list)
    bullets_en: List[str] = Field(default_factory=list)
    source: SourceType = Field(default="template", description="llm when the API answered")
    blocked: bool = Field(
        default=False, description="True when the guardrail replaced the model output"
    )
    provenance: Optional[Provenance] = None


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------
class ModelMetric(BaseModel):
    model_name: str
    metric: str
    value: float
    baseline_name: Optional[str] = None
    baseline_value: Optional[float] = None
    improvement_pct: Optional[float] = None


class FairnessRow(BaseModel):
    dimension: Dimension
    group: str
    metric: str
    value: float
    relative_gap_pct: float


class MetricsResponse(BaseModel):
    generated_at: datetime
    forecast: List[ModelMetric] = Field(default_factory=list)
    anomaly: List[ModelMetric] = Field(default_factory=list)
    signal: List[ModelMetric] = Field(default_factory=list)
    fairness: List[FairnessRow] = Field(default_factory=list)
    impact: List[ModelMetric] = Field(
        default_factory=list,
        description=(
            "Outcome metrics: fee savings, shortfall days avoided and the goal "
            "hit-rate backtest. Separate from the model blocks because these are "
            "consequences, not model accuracy."
        ),
    )
    feedback: Optional["FeedbackSummary"] = Field(
        default=None,
        description=(
            "Aggregated 'was this helpful?' responses, with no PII: only a count "
            "and rates per surface."
        ),
    )
    notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# GET /health-coach  (Financial Health Coach)
# ---------------------------------------------------------------------------
class HealthFactor(BaseModel):
    """One scored behaviour behind the 0-100 health score."""

    key: str
    label_en: str
    label_bn: str
    points: float = Field(description="Points earned for this factor")
    max_points: float = Field(description="Points this factor could earn")
    share: float = Field(ge=0.0, le=1.0, description="Earned fraction of the maximum")
    detail_en: str
    detail_bn: str


class HealthCoachResponse(BaseModel):
    """A coaching reading of behaviour in 0-100, never a credit score.

    The score is deliberately a coaching number, not a grade: it says how the
    observed habits read, and ``is_not_a_credit_score`` travels with it so no
    surface can present it as a lending signal.
    """

    user_id: str
    score: int = Field(ge=0, le=100, description="0-100 behaviour score")
    score_max: int = 100
    band: Literal["Fragile", "Building", "Steady", "Strong"]
    band_bn: str
    summary_bn: str = Field(description="Plain-language Bangla summary of the score")
    summary_en: str = Field(description="Plain-language English summary of the score")
    factors: List[HealthFactor] = Field(default_factory=list)
    arithmetic: List[str] = Field(default_factory=list, description="Step-by-step sum")
    is_not_a_credit_score: bool = True
    banner_bn: str = "এটি ক্রেডিট স্কোর বা ঋণের সিদ্ধান্ত নয়।"
    banner_en: str = "This is a coaching reading, not a credit score or a lending decision."
    provenance: Provenance


# ---------------------------------------------------------------------------
# POST /feedback  (was this helpful?)
# ---------------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    """A 'was this helpful?' tap. Nothing here identifies the person."""

    surface: str = Field(
        min_length=1,
        max_length=40,
        description="Which card the tap came from, e.g. forecast | savings_plan",
    )
    helpful: bool = Field(description="True for a thumbs-up, False for a thumbs-down")
    intent: Optional[str] = Field(
        default=None, max_length=40, description="Optional intent the answer served"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=280,
        description=(
            "Optional free text. It is intentionally NOT persisted (it could "
            "contain PII); only the fact that a comment was offered is stored."
        ),
    )


class FeedbackResponse(BaseModel):
    """The anonymised record that was written (never the raw user id)."""

    status: Literal["recorded"] = "recorded"
    recorded_at: datetime
    respondent: str = Field(description="Salted hash of the user id, never the id")
    surface: str
    helpful: bool
    stored_fields: List[str] = Field(default_factory=list)
    note: str = (
        "No PII is stored: the user id is salted-hashed and any comment text is discarded."
    )


class FeedbackSurfaceSummary(BaseModel):
    surface: str
    responses: int
    helpful: int
    helpful_rate_pct: float


class FeedbackSummary(BaseModel):
    """Aggregate of the feedback store, shown on the metrics page."""

    responses: int = 0
    helpful: int = 0
    helpful_rate_pct: float = 0.0
    by_surface: List[FeedbackSurfaceSummary] = Field(default_factory=list)
    note: str = (
        "Aggregated from the append-only store; no PII is recorded (ids are "
        "salted-hashed and free text is dropped)."
    )


# ---------------------------------------------------------------------------
# GET /goal-templates  (Goal Copilot)
# ---------------------------------------------------------------------------
class GoalTemplate(BaseModel):
    """A curated savings-goal shape (education, emergency fund, travel...)."""

    key: str
    label_en: str
    label_bn: str
    description_en: str
    description_bn: str
    default_months: int = Field(ge=1)
    suggested_goal_bdt: float = Field(ge=0, description="Scaled to the caller's income")
    goal_label_bn: str
    goal_label_en: str
    factors: List[str] = Field(
        default_factory=list, description="What usually drives the amount"
    )
    provenance: Provenance


class GoalTemplatesResponse(BaseModel):
    user_id: str
    templates: List[GoalTemplate] = Field(default_factory=list)


FeedbackSummary.model_rebuild()
MetricsResponse.model_rebuild()




