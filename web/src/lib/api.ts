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
}

export type PressureReason = "negative_net" | "below_buffer" | "both";

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
  net_source?: "model" | "difference";
}

export interface ForecastResponse {
  user_id: string;
  horizon_days: number;
  generated_at: string;
  generated_from: string | null;
  net_source: "model" | "difference";
  days: DayForecast[];
  pressure_days: string[];
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
  dimension: "persona" | "district" | "income_band";
  group: string;
  metric: string;
  value: number;
  relative_gap_pct: number;
}

export interface MetricsResponse {
  generated_at: string;
  forecast: ModelMetric[];
  anomaly: ModelMetric[];
  signal: ModelMetric[];
  fairness: FairnessRow[];
  notes: string[];
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEMO_TOKEN = process.env.NEXT_PUBLIC_DEMO_TOKEN ?? "change-me";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000);

  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Demo-Token": DEMO_TOKEN,
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new Error(`API ${path} failed with status ${response.status}`);
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

export function fetchCreditReadiness(): Promise<ConsistencySignalResponse> {
  return request<ConsistencySignalResponse>("/credit-readiness", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function fetchMetrics(): Promise<MetricsResponse> {
  return request<MetricsResponse>("/metrics");
}
