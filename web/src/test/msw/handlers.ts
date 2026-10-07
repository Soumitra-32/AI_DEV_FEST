import { http, HttpResponse } from "msw";
import type {
  HealthResponse,
  IdentityResponse,
  ForecastResponse,
  SavingsPlanResponse,
  AnomalyResponse,
  ExplainResponse,
  ConsistencySignalResponse,
  MetricsResponse,
  ParseGoalResponse,
} from "@/lib/api";

export const mockHealthResponse: HealthResponse = {
  status: "ok",
  version: "0.1.0",
  database: {
    available: true,
    path: "/data/demo.duckdb",
    users: 100,
    transactions: 5000,
    generated_at: "2026-10-01T00:00:00Z",
  },
  features: {
    forecast: true,
    savings_plan: true,
    anomalies: true,
    credit_readiness: true,
    feedback: true,
  },
  checked_at: "2026-10-07T10:00:00Z",
};

export const mockIdentityResponse: IdentityResponse = {
  user_id: "demo-user-1",
  name_en: "Rahim Uddin",
  name_bn: "রহিম উদ্দিন",
  persona: "shopkeeper",
  district: "Dhaka",
  income_band: "30k-50k",
  language_pref: "bn",
  cohort: "demo",
  is_demo_user: true,
};

export const mockForecastResponse: ForecastResponse = {
  user_id: "demo-user-1",
  horizon_days: 14,
  generated_at: "2026-10-07T10:00:00Z",
  generated_from: "2026-10-06",
  net_source: "difference",
  days: [
    {
      date: "2026-10-27",
      predicted_inflow_bdt: 12000,
      predicted_outflow_bdt: 4500,
      predicted_net_bdt: 7500,
      predicted_balance_bdt: 15500,
      is_pressure_day: false,
      pressure_reason: null,
    },
    {
      date: "2026-10-28",
      predicted_inflow_bdt: 2000,
      predicted_outflow_bdt: 18000,
      predicted_net_bdt: -16000,
      predicted_balance_bdt: -500,
      is_pressure_day: true,
      pressure_reason: "below_buffer",
    },
    {
      date: "2026-10-29",
      predicted_inflow_bdt: 8000,
      predicted_outflow_bdt: 3000,
      predicted_net_bdt: 5000,
      predicted_balance_bdt: 4500,
      is_pressure_day: false,
      pressure_reason: null,
    },
  ],
  pressure_days: ["2026-10-28"],
  drivers: [
    {
      feature: "rent_payment",
      direction: "increases",
      impact_bdt: 15000,
      detail: "Regular month-end shop rent",
    },
    {
      feature: "sales_deposit",
      direction: "decreases",
      impact_bdt: 5000,
      detail: "Anticipated weekend sales",
    },
  ],
  metrics: {
    model_name: "LightGBM",
    mae_bdt: 120,
    rmse_bdt: 180,
    baseline_name: "Trailing7d",
    baseline_mae_bdt: 240,
    improvement_pct: 50,
    net_mae_bdt: 150,
    net_baseline_name: "Trailing7d",
    net_improvement_pct: 45,
    net_source: "difference",
  },
  provenance: {
    prediction: "14-day cash forecast",
    assumption: "Recent spending patterns continue",
    explanation: "Calculated using Gradient Boosting on transactional history",
    source: "model",
  },
};

export const mockSavingsPlanResponse: SavingsPlanResponse = {
  user_id: "demo-user-1",
  goal_bdt: 30000,
  months: 6,
  feasible: true,
  required_monthly_bdt: 5000,
  forecasted_surplus_bdt: 7000,
  safety_buffer_bdt: 1500,
  feasible_monthly_bdt: 5500,
  arithmetic: [
    "required monthly = 30000 / 6 = 5000",
    "safety buffer = 1500",
    "feasible monthly = surplus 7000 - buffer 1500 = 5500",
    "feasible",
  ],
  trade_offs: [
    {
      action: "reduce",
      title: "Lower the target",
      description: "Keep 6 months, aim for ৳25,000",
      months: 6,
      target_bdt: 25000,
      monthly_amount_bdt: 4166,
      monthly_effect_bdt: -834,
    },
    {
      action: "delay",
      title: "Extend timeline",
      description: "Keep ৳30,000 target, extend to 7 months",
      months: 7,
      target_bdt: 30000,
      monthly_amount_bdt: 4285,
      monthly_effect_bdt: -715,
    },
  ],
  do_nothing: {
    description: "After 6 months you have ৳0 saved and paid about ৳1,200",
    estimated_cost_bdt: 1200,
    horizon_months: 6,
  },
  pressure_days: ["2026-10-28"],
  provenance: {
    prediction: "Savings plan feasible",
    assumption: "Monthly surplus remains stable",
    explanation: "Feasibility confirmed with safety buffer preserved",
    source: "rule",
  },
};

export const mockAnomalyResponse: AnomalyResponse = {
  user_id: "demo-user-1",
  window_days: 30,
  items: [
    {
      transaction_id: "tx-101",
      timestamp: "2026-10-05T14:30:00Z",
      amount_bdt: 2500,
      channel: "cash_out",
      category: "supplier",
      anomaly_type: "high_fee",
      score: 0.85,
      reason: "High cash-out fee paid",
      suggested_action: "switch",
      suggested_channel: "bangla_qr",
    },
  ],
  fee_switch: {
    cash_out_count: 5,
    cash_out_volume_bdt: 12500,
    fee_paid_bdt: 175,
    alternative_channel: "bangla_qr",
    alternative_fee_bdt: 0,
    potential_saving_bdt: 175,
    adoption_range: "0% - 100%",
    bangla_qr_eligible_count: 5,
    bangla_qr_eligible_volume_bdt: 12500,
    bangla_qr_cap_bdt: 50000,
    upay_issuer_incentive_bdt: 50,
  },
  provenance: {
    prediction: "Spending anomalies detected",
    assumption: "Bangla QR accepted at regular vendors",
    explanation: "Identified high cash-out transactions",
    source: "rule",
  },
};

export const mockExplainResponse: ExplainResponse = {
  intent: "savings_plan",
  answer_bn: "আপনার সঞ্চয় পরিকল্পনা বিশ্লেষণ করা হয়েছে।",
  answer_en: "Your savings plan has been analyzed.",
  bullets_bn: ["মাসিক ৫,০০০ টাকা সঞ্চয় প্রয়োজন"],
  bullets_en: ["Requires saving ৳5,000 per month"],
  source: "template",
  blocked: false,
  provenance: {
    prediction: "Query classified as savings plan",
    assumption: "User asked about monthly target",
    explanation: "Intent matched with high confidence",
    source: "rule",
  },
};

export const mockCreditReadinessResponse: ConsistencySignalResponse = {
  user_id: "demo-user-1",
  band: "Steady",
  factors: [
    {
      feature: "inflow_consistency",
      direction: "improves",
      magnitude: 0.75,
      plain_language: "Regular monthly inflows",
    },
  ],
  improvements: ["Maintain positive balance near month-end"],
  not_a_decision: true,
  banner_en: "This is a consistency signal, not a credit decision.",
  banner_bn: "এটি ধারাবাহিকতার সূচক, কোনো ঋণ অনুমোদন বা প্রত্যাখ্যানের সিদ্ধান্ত নয়।",
  auc: 0.78,
  provenance: {
    prediction: "Consistency band: Steady",
    assumption: "Last 6 months turnover",
    explanation: "Evaluated using heuristic stability metrics",
    source: "model",
  },
};

export const mockMetricsResponse: MetricsResponse = {
  generated_at: "2026-10-07T10:00:00Z",
  forecast: [
    {
      model_name: "LightGBM",
      metric: "MAE",
      value: 120,
      baseline_name: "Trailing7d",
      baseline_value: 240,
      improvement_pct: 50,
    },
  ],
  anomaly: [
    {
      model_name: "IsolationForest",
      metric: "Precision",
      value: 0.92,
      baseline_name: "RuleBased",
      baseline_value: 0.8,
      improvement_pct: 15,
    },
  ],
  signal: [
    {
      model_name: "LogisticRegression",
      metric: "ROC-AUC",
      value: 0.81,
      baseline_name: "Random",
      baseline_value: 0.5,
      improvement_pct: 62,
    },
  ],
  fairness: [
    {
      dimension: "gender",
      group: "female",
      metric: "approval_rate",
      value: 0.48,
      relative_gap_pct: 0.04,
      exceeds_target: false,
    },
  ],
  customer_impact: {
    total_feedback: 12,
    helpful_responses: 11,
    helpful_feedback_rate_pct: 91.7,
    understanding_responses: 10,
    understood_count: 9,
    understanding_rate_pct: 90.0,
    recommendations_shown: 25,
    recommendations_accepted: 18,
    recommendations_rejected: 4,
    actions_completed: 12,
    recommendation_acceptance_rate_pct: 72.0,
    action_completion_rate_pct: 66.7,
    savings_plans_created: 14,
    savings_plans_viewed: 22,
    forecast_views: 30,
    anomaly_views: 15,
    copilot_usage: 45,
    has_data: true,
    message: "Real customer interaction telemetry aggregated without fabrication",
  },
};

export const mockParseGoalResponse: ParseGoalResponse = {
  goal_bdt: 30000,
  months: 6,
  is_complete: true,
};

export const mockFeedbackResponse = {
  status: "recorded" as const,
  recorded_at: "2026-10-07T10:00:00Z",
  respondent: "demo-anon-id",
  surface: "plan",
  feature: "savings_plan",
  helpful: true,
  understood: true,
  acted_on: true,
  rating: 5,
  recommendation_id: null,
  stored_fields: ["recorded_at", "respondent", "surface", "helpful"],
  note: "No PII is stored: the user id is salted-hashed and any comment text is discarded.",
};

export const mockProductEventResponse = {
  status: "recorded" as const,
  recorded_at: "2026-10-07T10:00:00Z",
  respondent: "demo-anon-id",
  event_type: "recommendation_accepted",
  feature: "tips",
  recommendation_id: "tip-1",
  properties: {},
};

export const handlers = [
  http.get("*/health", () => HttpResponse.json(mockHealthResponse)),
  http.get("*/me", () => HttpResponse.json(mockIdentityResponse)),
  http.post("*/forecast", () => HttpResponse.json(mockForecastResponse)),
  http.post("*/savings-plan", () => HttpResponse.json(mockSavingsPlanResponse)),
  http.post("*/anomalies", () => HttpResponse.json(mockAnomalyResponse)),
  http.post("*/chat-explain", () => HttpResponse.json(mockExplainResponse)),
  http.post("*/credit-readiness", () => HttpResponse.json(mockCreditReadinessResponse)),
  http.get("*/metrics", () => HttpResponse.json(mockMetricsResponse)),
  http.post("*/parse-goal", () => HttpResponse.json(mockParseGoalResponse)),
  http.post("*/feedback", () => HttpResponse.json(mockFeedbackResponse)),
  http.post("*/events", () => HttpResponse.json(mockProductEventResponse)),
];
