"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FileSearch, Loader2, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";

import {
  Badge,
  Button,
  DashboardCard,
  MetricCard,
  Notice,
  PageShell,
  SectionHeader,
} from "@/components/ui";
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

const FIELD_CLASSNAME =
  "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition duration-200 placeholder:text-slate-400 focus:border-slate-300 focus:ring-4 focus:ring-slate-100";

function parsePercent(value: string | number): number {
  const parsed = Number(String(value).replace("%", "").trim());
  if (!Number.isFinite(parsed)) return 0;
  return parsed <= 1 ? parsed * 100 : parsed;
}

function formatPercentLabel(value: number): string {
  return `${new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)}%`;
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
    .filter((value): value is number => value !== null);

  const avgRelevance = relevances.length
    ? relevances.reduce((a, b) => a + b, 0) / relevances.length
    : 62;
  const densityBoost = Math.min(result.supporting_evidence.length * 8, 30);
  return Math.min(100, Math.round(avgRelevance * 0.72 + densityBoost));
}

export default function VerifyPage() {
  const headlineInputRef = useRef<HTMLInputElement>(null);
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

  useEffect(() => {
    const focusHeadline = () => headlineInputRef.current?.focus();
    window.addEventListener("focus-verify-input", focusHeadline);
    return () => window.removeEventListener("focus-verify-input", focusHeadline);
  }, []);

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
    <PageShell>
      <SectionHeader
        title="Intelligence Engine"
        description="Multi-weighted scoring across ML confidence, source priority, and evidence consensus in a single analyst workflow."
        action={<Badge>RoBERTa + ChromaDB</Badge>}
      />

      {serviceOffline ? (
        <Notice tone="danger" className="mb-6">
          Service Offline. Start FastAPI (`uvicorn api.app:app`) and try again.
        </Notice>
      ) : null}

      <DashboardCard className="p-8">
        <div className="space-y-4">
          <input
            ref={headlineInputRef}
            value={headline}
            onChange={(event) => setHeadline(event.target.value)}
            placeholder="Paste a headline (10-500 chars) to verify..."
            className={FIELD_CLASSNAME}
          />
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Optional: paste article content/body for better reliability..."
            rows={6}
            className={`${FIELD_CLASSNAME} resize-y`}
          />

          <Button type="button" onClick={handleVerify} disabled={loading} className="w-full sm:w-auto">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {loading ? "Running Multi-Weighted Analysis..." : "Run AI Verification"}
          </Button>
        </div>

        {loading ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <div className="mb-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-1/3 animate-pulse rounded-full bg-slate-700" />
            </div>
            <p className="text-sm text-slate-600">
              Computing ML confidence, source priority, and evidence consensus...
            </p>
          </div>
        ) : null}

        {error ? <p className="mt-4 text-sm text-red-600">{error}</p> : null}
      </DashboardCard>

      {result ? (
        <section className="mt-6 space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="Trust Score" value={formatPercentLabel(trustScore)} subtitle="Weighted final result" />
            <MetricCard title="ML Confidence" value={formatPercentLabel(mlConfidence)} subtitle="RoBERTa model output" />
            <MetricCard title="Source Score" value={formatPercentLabel(sourceScore)} subtitle="NewsData priority weight" />
            <MetricCard title="Consensus Score" value={formatPercentLabel(consensusScore)} subtitle="ChromaDB evidence density" />
          </div>

          <DashboardCard>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900">Verification Decision</h2>
              <Badge
                tone={result.prediction === "FAKE" ? "danger" : "success"}
                className="shadow-[inset_0_1px_0_rgba(255,255,255,0.4)]"
              >
                {result.prediction === "FAKE" ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
                {result.prediction}
              </Badge>
            </div>
            <p className="text-sm text-slate-600">{result.headline}</p>

            {result.warnings?.length ? (
              <Notice tone="warning" className="mt-4">
                {result.warnings.map((warning, index) => (
                  <p key={`${warning}-${index}`} className="text-xs text-amber-700">
                    {warning}
                  </p>
                ))}
              </Notice>
            ) : null}

            <div className="mt-5 border-t border-slate-200 pt-4">
              <p className="mb-2 text-xs text-slate-500">Help Improve Model (Human Feedback)</p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="success"
                  type="button"
                  onClick={() => handleFeedback("REAL")}
                  disabled={feedbackLoading !== null}
                >
                  {feedbackLoading === "REAL" ? <Loader2 size={14} className="animate-spin" /> : null}
                  Mark as REAL
                </Button>
                <Button
                  variant="danger"
                  type="button"
                  onClick={() => handleFeedback("FAKE")}
                  disabled={feedbackLoading !== null}
                >
                  {feedbackLoading === "FAKE" ? <Loader2 size={14} className="animate-spin" /> : null}
                  Mark as FAKE
                </Button>
              </div>
              {feedbackMessage ? <p className="mt-2 text-xs text-slate-600">{feedbackMessage}</p> : null}
              {feedbackError ? <p className="mt-2 text-xs text-red-600">{feedbackError}</p> : null}
            </div>
          </DashboardCard>

          <DashboardCard>
            <h2 className="mb-4 text-lg font-semibold text-slate-900">Verification Evidence</h2>
            {result.supporting_evidence?.length ? (
              <div className="space-y-3">
                {result.supporting_evidence.map((item, index) => (
                  <article key={`${item.url}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                    <p className="text-sm font-medium text-slate-900">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">Source: {item.source}</p>
                    {item.url ? (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 block break-all text-sm text-slate-600 transition hover:text-slate-900 hover:underline"
                      >
                        {item.url}
                      </a>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <EmptyVerificationState />
            )}
          </DashboardCard>
        </section>
      ) : null}
    </PageShell>
  );
}

function EmptyVerificationState() {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-6 py-10 text-center shadow-inner">
      <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-400 shadow-sm">
        <FileSearch size={18} />
      </div>
      <p className="text-sm font-medium text-slate-900">No data available yet</p>
      <p className="mt-2 text-sm text-slate-500">
        No corroborating evidence was found for this headline in the current knowledge base.
      </p>
    </div>
  );
}
