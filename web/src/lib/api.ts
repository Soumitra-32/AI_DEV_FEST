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
