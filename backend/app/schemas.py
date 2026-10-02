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
    net_source: Literal["model", "difference"] = Field(
        default="model",
        description=(
            "Whether predicted net came from the dedicated net model or from "
            "inflow minus outflow; 'difference' is the weaker number"
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
    notes: List[str] = Field(default_factory=list)



