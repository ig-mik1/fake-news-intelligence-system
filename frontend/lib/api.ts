const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const FALLBACK_BASE_URLS = ["http://127.0.0.1:8000"];

async function fetchWithFallback(path: string, init?: RequestInit): Promise<Response> {
  const candidates = [API_BASE_URL, ...FALLBACK_BASE_URLS].filter(
    (value, index, array) => array.indexOf(value) === index
  );

  let lastError: unknown;
  for (const baseUrl of candidates) {
    try {
      return await fetch(`${baseUrl}${path}`, init);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Service Offline: backend is unreachable.");
}

export interface VerifyPayload {
  headline: string;
  content?: string;
}

export interface EvidenceItem {
  title: string;
  source: string;
  url: string;
  relevance?: number;
}

export interface VerifyResponse {
  headline: string;
  trust_score: string | number;
  ml_confidence: string | number;
  trust_score_percent?: string;
  ml_confidence_percent?: string;
  ml_fake_probability?: number;
  evidence_score?: number;
  source_score?: number;
  decision?: "REAL" | "FAKE";
  prediction: string;
  supporting_evidence: EvidenceItem[];
  warnings: string[];
}

export interface FeedbackPayload {
  headline: string;
  content?: string;
  model_decision?: "REAL" | "FAKE";
  human_label: "REAL" | "FAKE";
  notes?: string;
}

export interface FeedbackResponse {
  status: "ok" | "ignored";
  message: string;
  storage_path?: string;
  review_status?: "pending";
  retry_after_seconds?: number;
}

export async function postVerification(payload: VerifyPayload): Promise<VerifyResponse> {
  const res = await fetchWithFallback("/api/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = "Verification failed";
    try {
      const err = await res.json();
      detail = err?.detail || detail;
    } catch {
      // Fall back to default error message.
    }
    throw new Error(typeof detail === "string" ? detail : "Verification failed");
  }

  return res.json();
}

export async function postFeedback(payload: FeedbackPayload): Promise<FeedbackResponse> {
  const res = await fetchWithFallback("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = "Feedback submission failed";
    try {
      const err = await res.json();
      detail = err?.detail || detail;
    } catch {
      // Fall back to default error message.
    }
    throw new Error(typeof detail === "string" ? detail : "Feedback submission failed");
  }

  return res.json();
}

export interface MonitoringItem {
  id: string;
  title: string;
  source: string;
  platform: string;
  url: string;
  ingested_at: string;
}

export interface MonitoringLatestResponse {
  status: string;
  count: number;
  active_sources?: number;
  items: MonitoringItem[];
  source?: string;
  error?: string;
}

export async function getMonitoringLatest(limit = 20): Promise<MonitoringLatestResponse> {
  const res = await fetchWithFallback(`/api/monitoring/latest?limit=${limit}`, {
    method: "GET",
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Service Offline: Monitoring API request failed.");
  return res.json();
}

export interface DashboardSummaryResponse {
  status: string;
  total_articles: number;
  fake_count: number;
  real_count: number;
  unknown_count: number;
  source_distribution: Record<string, number>;
  estimated_from_sample: boolean;
  sample_size: number;
}

export async function getDashboardSummary(sampleSize = 50): Promise<DashboardSummaryResponse> {
  const res = await fetchWithFallback(`/api/dashboard/summary?sample_size=${sampleSize}`, {
    method: "GET",
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Service Offline: Dashboard API request failed.");
  return res.json();
}
