/**
 * Minimal typed client for the FastAPI shell.
 *
 * Phase 2 implements only /health and /me, but the base URL, the demo-token
 * header, and the shared response shapes are fixed here so later phase routers
 * can be added without touching any component.
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
  /** net is the number the savings plan is solved from, so it is measured too */
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

/** POST /chat-explain — the Bangla-first assistant's answer in both languages. */
export interface ExplainRequest {
  message: string;
  language?: "bn" | "en";
  /** Optional client hint; the server always re-classifies and ignores it. */
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
  /** "llm" when the model wrote it, "template" when the fallback answered. */
  source: "rule" | "model" | "template" | "llm";
  /** True when the guardrail replaced a generated answer. */
  blocked: boolean;
  provenance: Provenance | null;
}

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEMO_TOKEN = process.env.NEXT_PUBLIC_DEMO_TOKEN ?? "change-me";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
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
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function fetchIdentity(): Promise<IdentityResponse> {
  return request<IdentityResponse>("/me");
}
/** POST /forecast — the 14-day cash-flow forecast plus pressure days. */
export function fetchForecast(body: ForecastRequest = {}): Promise<ForecastResponse> {
  return request<ForecastResponse>("/forecast", {
    method: "POST",
    body: JSON.stringify({
      horizon_days: body.horizon_days ?? 14,
      include_pressure_days: body.include_pressure_days ?? true,
    }),
  });
}

/** POST /savings-plan — feasibility, trade-offs and the do-nothing cost. */
export function fetchSavingsPlan(body: SavingsPlanRequest): Promise<SavingsPlanResponse> {
  return request<SavingsPlanResponse>("/savings-plan", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** POST /chat-explain — ask one question in Bangla or English. */
export function fetchExplain(
  body: ExplainRequest,
): Promise<ExplainResponse> {
  return request<ExplainResponse>("/chat-explain", {
    method: "POST",
    body: JSON.stringify({
      message: body.message,
      language: body.language ?? "bn",
    }),
  });
}
