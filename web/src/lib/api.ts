/**
 * Minimal typed client for the FastAPI backend.
 * All types mirror backend/app/schemas.py frozen contracts.
 */

export interface DatabaseInfo {
  available: boolean;
  path: string;
  users: number;
  transactions: number;
  generated_at: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  database: DatabaseInfo;
  features: Record<string, boolean>;
  checked_at: string;
}

export interface IdentityResponse {
  user_id: string;
  name_en: string;
  name_bn: string;
  persona: string | null;
  district: string | null;
  income_band: string | null;
  language_pref: "bn" | "en";
  cohort: string;
  is_demo_user: boolean;
}

export interface Provenance {
  prediction: string;
  assumption: string;
  explanation: string;
  source: "rule" | "model" | "template" | "llm";
}

/** POST /forecast */
export interface ForecastRequest {
  horizon_days?: number;
  include_pressure_days?: boolean;
  include_drivers?: boolean;
  /** Language for the SHAP driver explanations (bn | en). */
  language?: "bn" | "en";
  as_of?: string;
}

export type PressureReason = "below_buffer" | "both";

export interface DayForecast {
  date: string;
  predicted_inflow_bdt: number;
  predicted_outflow_bdt: number;
  predicted_net_bdt: number;
  predicted_balance_bdt: number | null;
  is_pressure_day: boolean;
  pressure_reason: PressureReason | null;
}

export interface ForecastMetrics {
  model_name: string;
  mae_bdt: number;
  rmse_bdt: number;
  baseline_name: string;
  baseline_mae_bdt: number;
  improvement_pct: number;
  net_mae_bdt?: number;
  net_baseline_name?: string;
  net_improvement_pct?: number;
  net_source?: "model" | "difference" | "anchor";
}

export interface Driver {
  feature: string;
  direction: "increases" | "decreases";
  impact_bdt: number;
  detail: string;
}

export interface ForecastResponse {
  user_id: string;
  horizon_days: number;
  generated_at: string;
  generated_from: string | null;
  net_source: "model" | "difference" | "anchor";
  days: DayForecast[];
  pressure_days: string[];
  drivers: Driver[];
  metrics: ForecastMetrics | null;
  provenance: Provenance;
}

/** POST /savings-plan */
export interface SavingsPlanRequest {
  goal_bdt: number;
  months: number;
  goal_label?: string | null;
}

export type TradeOffAction = "reduce" | "delay" | "switch" | "do_nothing";

export interface TradeOffOption {
  action: TradeOffAction;
  title: string;
  description: string;
  months: number | null;
  target_bdt: number | null;
  monthly_amount_bdt: number | null;
  monthly_effect_bdt: number | null;
}

export interface DoNothingOutcome {
  description: string;
  estimated_cost_bdt: number;
  horizon_months: number;
}

export interface SavingsPlanResponse {
  user_id: string;
  goal_bdt: number;
  months: number;
  feasible: boolean;
  required_monthly_bdt: number;
  forecasted_surplus_bdt: number;
  safety_buffer_bdt: number;
  feasible_monthly_bdt: number;
  arithmetic: string[];
  trade_offs: TradeOffOption[];
  do_nothing: DoNothingOutcome;
  pressure_days: string[];
  provenance: Provenance;
}

/** POST /anomalies (Spending Companion) */
export interface AnomalyRequest {
  window_days?: number;
  limit?: number;
}

export interface AnomalyItem {
  transaction_id: string;
  timestamp: string;
  amount_bdt: number;
  channel: string;
  category: string;
  anomaly_type: string | null;
  score: number | null;
  reason: string;
  suggested_action: TradeOffAction;
  suggested_channel: string | null;
}

export interface FeeSwitchSuggestion {
  cash_out_count: number;
  cash_out_volume_bdt: number;
  fee_paid_bdt: number;
  alternative_channel: string;
  alternative_fee_bdt: number;
  potential_saving_bdt: number;
  adoption_range: string;
  bangla_qr_eligible_count?: number;
  bangla_qr_eligible_volume_bdt?: number;
  bangla_qr_cap_bdt?: number;
  upay_issuer_incentive_bdt?: number;
  bangla_qr_policy?: {
    effective_date: string;
    incentive_cap_bdt: number;
    issuer_incentive_pct: number;
    acquirer_incentive_pct: number;
    instant_settlement: boolean;
    interchange_rate_pct: number;
    merchant_mdr_min_abolished: boolean;
    customer_fee_pct: number;
    anti_misuse_monitoring: string;
  };
  arithmetic?: string[];
}

export interface AnomalyResponse {
  user_id: string;
  window_days: number;
  items: AnomalyItem[];
  fee_switch: FeeSwitchSuggestion | null;
  provenance: Provenance;
}

/** POST /chat-explain */
export interface ExplainRequest {
  message: string;
  language?: "bn" | "en";
  intent?: ExplainIntent | null;
}

export type ExplainIntent =
  | "explain_transactions"
  | "forecast"
  | "savings_plan"
  | "fees"
  | "consistency"
  | "tips"
  | "unknown";

export interface ExplainResponse {
  intent: ExplainIntent;
  answer_bn: string;
  answer_en: string;
  bullets_bn: string[];
  bullets_en: string[];
  source: "rule" | "model" | "template" | "llm";
  blocked: boolean;
  provenance: Provenance | null;
}

/** POST /credit-readiness */
export type ConsistencyBand = "Building" | "Steady" | "Strong";

export interface SignalFactor {
  feature: string;
  direction: "improves" | "weakens";
  magnitude: number;
  plain_language: string;
}

export interface ConsistencySignalResponse {
  user_id: string;
  band: ConsistencyBand;
  factors: SignalFactor[];
  improvements: string[];
  not_a_decision: boolean;
  banner_en: string;
  banner_bn: string;
  auc: number | null;
  provenance: Provenance;
}

/** GET /metrics */
export interface ModelMetric {
  model_name: string;
  metric: string;
  value: number;
  baseline_name: string | null;
  baseline_value: number | null;
  improvement_pct: number | null;
}

export interface FairnessRow {
  dimension: string;
  group: string;
  metric: string;
  value: number;
  relative_gap_pct: number;
  exceeds_target?: boolean;
}

export interface CustomerImpactSummary {
  total_feedback: number;
  helpful_responses: number;
  helpful_feedback_rate_pct: number | null;
  understanding_responses: number;
  understood_count: number;
  understanding_rate_pct: number | null;
  recommendations_shown: number;
  recommendations_accepted: number;
  recommendations_rejected: number;
  actions_completed: number;
  recommendation_acceptance_rate_pct: number | null;
  action_completion_rate_pct: number | null;
  savings_plans_created: number;
  savings_plans_viewed: number;
  forecast_views: number;
  anomaly_views: number;
  copilot_usage: number;
  has_data: boolean;
  message: string;
}

export interface FeedbackSurfaceSummary {
  surface: string;
  responses: number;
  helpful: number;
  helpful_rate_pct: number;
}

export interface FeedbackSummary {
  responses: number;
  helpful: number;
  helpful_rate_pct: number;
  by_surface: FeedbackSurfaceSummary[];
}

export interface MetricsResponse {
  generated_at: string;
  forecast: ModelMetric[];
  anomaly: ModelMetric[];
  signal: ModelMetric[];
  fairness: FairnessRow[];
  impact?: ModelMetric[];
  feedback?: FeedbackSummary | null;
  customer_impact?: CustomerImpactSummary | null;
  notes?: string[];
}

export interface FeedbackRequest {
  feature?: string;
  surface?: string;
  helpful: boolean;
  understood?: boolean;
  acted_on?: boolean;
  rating?: number;
  intent?: string;
  recommendation_id?: string;
  comment?: string;
}

export interface FeedbackResponse {
  status: "recorded";
  recorded_at: string;
  respondent: string;
  surface: string;
  feature: string;
  helpful: boolean;
  understood?: boolean | null;
  acted_on?: boolean | null;
  rating?: number | null;
  recommendation_id?: string | null;
  stored_fields: string[];
  note: string;
}

export type ProductEventType =
  | "forecast_viewed"
  | "savings_plan_viewed"
  | "savings_plan_created"
  | "recommendation_shown"
  | "recommendation_accepted"
  | "recommendation_rejected"
  | "recommendation_action_completed"
  | "recommendation_feedback"
  | "anomaly_viewed"
  | "copilot_used"
  | "feedback_submitted";

export interface ProductEventRequest {
  event_type: ProductEventType;
  feature?: string;
  recommendation_id?: string;
  properties?: Record<string, any>;
}

export interface ProductEventResponse {
  status: "recorded";
  recorded_at: string;
  respondent: string;
  event_type: string;
  feature?: string | null;
  recommendation_id?: string | null;
  properties: Record<string, any>;
}

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const DEMO_TOKEN = process.env.NEXT_PUBLIC_DEMO_TOKEN ?? "change-me";

export class ApiError extends Error {
  status: number;
  path: string;

  constructor(message: string, status: number, path: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
  }
}

export function buildApiUrl(path: string, base: string = BASE_URL): string {
  const cleanBase = base.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

export async function request<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = 60000,
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = buildApiUrl(path);
    const response = await fetch(url, {
      ...init,
      signal: init?.signal ?? controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Demo-Token": DEMO_TOKEN,
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new ApiError(`API ${path} failed with status ${response.status}`, response.status, path);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function fetchIdentity(): Promise<IdentityResponse> {
  return request<IdentityResponse>("/me");
}

export function fetchForecast(body: ForecastRequest = {}): Promise<ForecastResponse> {
  return request<ForecastResponse>("/forecast", {
    method: "POST",
    body: JSON.stringify({
      horizon_days: body.horizon_days ?? 14,
      include_pressure_days: body.include_pressure_days ?? true,
      include_drivers: body.include_drivers ?? true,
      language: body.language ?? "bn",
      ...(body.as_of ? { as_of: body.as_of } : {}),
    }),
  });
}

export function fetchSavingsPlan(body: SavingsPlanRequest): Promise<SavingsPlanResponse> {
  return request<SavingsPlanResponse>("/savings-plan", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchAnomalies(body: AnomalyRequest = {}): Promise<AnomalyResponse> {
  return request<AnomalyResponse>("/anomalies", {
    method: "POST",
    body: JSON.stringify({
      window_days: body.window_days ?? 30,
      limit: body.limit ?? 20,
    }),
  });
}

export function fetchExplain(body: ExplainRequest): Promise<ExplainResponse> {
  return request<ExplainResponse>("/chat-explain", {
    method: "POST",
    body: JSON.stringify({
      message: body.message,
      language: body.language ?? "bn",
    }),
  });
}

export function fetchCreditReadiness(language: "bn" | "en" = "bn"): Promise<ConsistencySignalResponse> {
  return request<ConsistencySignalResponse>(`/credit-readiness?language=${language}`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function fetchMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>("/metrics");
}

/** POST /parse-goal (public: no user data, pure text parsing) */
export interface ParseGoalResponse {
  goal_bdt: number | null;
  months: number | null;
  is_complete: boolean;
}

export function fetchParseGoal(message: string): Promise<ParseGoalResponse> {
  return request<ParseGoalResponse>("/parse-goal", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function postFeedback(body: FeedbackRequest): Promise<FeedbackResponse> {
  return request<FeedbackResponse>("/feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function trackEvent(
  eventType: ProductEventType,
  options?: {
    feature?: string;
    recommendation_id?: string;
    properties?: Record<string, any>;
  },
): Promise<ProductEventResponse | null> {
  return request<ProductEventResponse>("/events", {
    method: "POST",
    body: JSON.stringify({
      event_type: eventType,
      feature: options?.feature,
      recommendation_id: options?.recommendation_id,
      properties: options?.properties ?? {},
    }),
  }).catch((err) => {
    // Non-blocking telemetry tracking
    if (process.env.NODE_ENV !== "test") {
      console.warn("Telemetry event failed to send:", err);
    }
    return null;
  });
}
