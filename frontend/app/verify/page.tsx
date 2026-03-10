"use client";

import { useMemo, useState } from "react";
import { Loader2, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";

import { postFeedback, postVerification, type VerifyResponse } from "@/lib/api";

const SOURCE_PRIORITY: Record<string, number> = {
  newsdata: 92,
  newsapi: 88,
  rss: 74,
  reuters: 90,
  associatedpress: 90,
  bbc: 88,
  reddit: 56,
  unknown: 50,
};

function parsePercent(value: string | number): number {
  const parsed = Number(String(value).replace("%", "").trim());
  if (!Number.isFinite(parsed)) return 0;
  return parsed <= 1 ? parsed * 100 : parsed;
}

function normalizeSource(raw: string): string {
  return raw.toLowerCase().replace(/\s+/g, "");
}

function computeSourceScore(result: VerifyResponse | null): number {
  if (!result?.supporting_evidence?.length) return 50;
  const scores = result.supporting_evidence.map((ev) => {
    const key = normalizeSource(ev.source || "unknown");
    return SOURCE_PRIORITY[key] ?? SOURCE_PRIORITY.unknown;
  });
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
}

function computeConsensusScore(result: VerifyResponse | null): number {
  if (!result?.supporting_evidence?.length) return 28;
  const relevances = result.supporting_evidence
    .map((ev) => (typeof ev.relevance === "number" ? ev.relevance : null))
    .filter((v): v is number => v !== null);

  const avgRelevance = relevances.length
    ? relevances.reduce((a, b) => a + b, 0) / relevances.length
    : 62;
  const densityBoost = Math.min(result.supporting_evidence.length * 8, 30);
  return Math.min(100, Math.round(avgRelevance * 0.72 + densityBoost));
}

export default function VerifyPage() {
  const [headline, setHeadline] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceOffline, setServiceOffline] = useState(false);
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState<"REAL" | "FAKE" | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  const trustScore = useMemo(() => parsePercent(result?.trust_score ?? "0"), [result]);
  const mlConfidence = useMemo(() => parsePercent(result?.ml_confidence ?? "0"), [result]);
  const sourceScore = useMemo(() => computeSourceScore(result), [result]);
  const consensusScore = useMemo(() => computeConsensusScore(result), [result]);

  const handleVerify = async () => {
    const cleaned = headline.trim();
    if (cleaned.length < 10 || cleaned.length > 500) {
      setError("Headline must be between 10 and 500 characters.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setServiceOffline(false);
      setFeedbackMessage(null);
      setFeedbackError(null);
      const cleanedContent = content.trim();
      const data = await postVerification({
        headline: cleaned,
        content: cleanedContent ? cleanedContent : undefined,
      });
      setResult(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Verification failed.";
      const offline = /failed to fetch|networkerror|service unavailable|load failed/i.test(message);
      setServiceOffline(offline);
      setError(offline ? "Service Offline: Backend is unreachable right now." : message);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (humanLabel: "REAL" | "FAKE") => {
    if (!result) return;
    try {
      setFeedbackLoading(humanLabel);
      setFeedbackError(null);
      setFeedbackMessage(null);

      const feedback = await postFeedback({
        headline: result.headline || headline.trim(),
        content: content.trim() || undefined,
        model_decision: result.prediction === "FAKE" ? "FAKE" : "REAL",
        human_label: humanLabel,
      });

      if (feedback.status === "ignored") {
        setFeedbackMessage(
          feedback.retry_after_seconds
            ? `Duplicate ignored. Try again in ~${feedback.retry_after_seconds}s.`
            : feedback.message
        );
      } else {
        setFeedbackMessage("Thanks. Feedback captured and queued for review.");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to submit feedback.";
      setFeedbackError(message);
    } finally {
      setFeedbackLoading(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-6 pb-10">
      {serviceOffline ? (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Service Offline. Start FastAPI (`uvicorn api.app:app`) and try again.
        </div>
      ) : null}

      <section className="rounded-3xl border border-white/40 bg-white/60 p-8 shadow-xl backdrop-blur-xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Intelligence Engine</h1>
            <p className="mt-2 text-sm text-slate-500">
              Multi-weighted scoring: ML confidence + source priority + evidence consensus.
            </p>
          </div>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
            RoBERTa + ChromaDB
          </span>
        </div>

        <div className="space-y-4">
          <input
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
            placeholder="Paste a headline (10-500 chars) to verify..."
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Optional: paste article content/body for better reliability..."
            rows={6}
            className="w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
          />

          <button
            type="button"
            onClick={handleVerify}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {loading ? "Running Multi-Weighted Analysis..." : "Run AI Verification"}
          </button>
        </div>

        {loading ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-1/3 animate-pulse rounded-full bg-slate-700" />
            </div>
            <p className="text-sm text-slate-600">
              Computing ML confidence, source priority, and evidence consensus...
            </p>
          </div>
        ) : null}

        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      </section>

      {result ? (
        <section className="mt-8 space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ScoreCard label="Trust Score" value={`${trustScore}%`} sub="Weighted Final Result" />
            <ScoreCard label="ML Confidence" value={`${mlConfidence}%`} sub="RoBERTa Model Output" />
            <ScoreCard label="Source Score" value={`${sourceScore}%`} sub="NewsData Priority Weight" />
            <ScoreCard label="Consensus Score" value={`${consensusScore}%`} sub="ChromaDB Evidence Density" />
          </div>

          <div className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-lg backdrop-blur-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">Verification Decision</h2>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
                  result.prediction === "FAKE" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"
                }`}
              >
                {result.prediction === "FAKE" ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
                {result.prediction}
              </span>
            </div>
            <p className="text-sm text-slate-600">{result.headline}</p>

            {result.warnings?.length ? (
              <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
                {result.warnings.map((warning, idx) => (
                  <p key={`${warning}-${idx}`} className="text-xs text-amber-800">
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}

            <div className="mt-5 border-t border-slate-200 pt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Help Improve Model (Human Feedback)
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleFeedback("REAL")}
                  disabled={feedbackLoading !== null}
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {feedbackLoading === "REAL" ? <Loader2 size={14} className="animate-spin" /> : null}
                  Mark as REAL
                </button>
                <button
                  type="button"
                  onClick={() => handleFeedback("FAKE")}
                  disabled={feedbackLoading !== null}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {feedbackLoading === "FAKE" ? <Loader2 size={14} className="animate-spin" /> : null}
                  Mark as FAKE
                </button>
              </div>
              {feedbackMessage ? <p className="mt-2 text-xs text-slate-600">{feedbackMessage}</p> : null}
              {feedbackError ? <p className="mt-2 text-xs text-red-600">{feedbackError}</p> : null}
            </div>
          </div>

          <div className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-lg backdrop-blur-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">Verification Evidence</h2>
            {result.supporting_evidence?.length ? (
              <div className="space-y-3">
                {result.supporting_evidence.map((item, index) => (
                  <article key={`${item.url}-${index}`} className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">Source: {item.source}</p>
                    {item.url ? (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 block break-all text-xs text-blue-600 hover:underline"
                      >
                        {item.url}
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No corroborating evidence found for this headline.</p>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function ScoreCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded-2xl border border-white/40 bg-white/60 p-5 shadow-lg backdrop-blur-xl">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{sub}</p>
    </div>
  );
}