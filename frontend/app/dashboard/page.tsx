"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ShieldCheck, Sigma } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import CommandCard from "@/components/command-card";
import { getDashboardSummary, type DashboardSummaryResponse } from "@/lib/api";

function toRiskColor(value: number): string {
  if (value >= 75) return "#dc2626";
  if (value >= 50) return "#f59e0b";
  return "#16a34a";
}

function pct(part: number, total: number): number {
  if (!total) return 0;
  return Math.round((part / total) * 10000) / 100;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getDashboardSummary(60);
        setSummary(data);
      } catch {
        setError("Service Offline: Could not load dashboard metrics.");
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const totals = useMemo(() => {
    const fake = summary?.fake_count ?? 0;
    const real = summary?.real_count ?? 0;
    const unknown = summary?.unknown_count ?? 0;
    const classified = fake + real;
    const trustRate = pct(real, classified || fake + real + unknown);
    return { fake, real, unknown, classified, trustRate };
  }, [summary]);

  const distributionData = useMemo(
    () => [
      { name: "Real", value: totals.real, fill: "#16a34a" },
      { name: "Fake", value: totals.fake, fill: "#dc2626" },
      { name: "Unknown", value: totals.unknown, fill: "#64748b" },
    ].filter((d) => d.value > 0),
    [totals]
  );

  const heatmapData = useMemo(() => {
    if (!summary) return [];
    const entries = Object.entries(summary.source_distribution);
    if (!entries.length) return [];

    const maxCount = Math.max(...entries.map(([, count]) => count), 1);
    const fakeRate = pct(totals.fake, Math.max(totals.classified, 1));
    const unknownRate = pct(totals.unknown, Math.max(summary.total_articles, 1));

    return entries
      .map(([source, count]) => {
        const volumeWeight = (count / maxCount) * 35;
        const score = Math.min(100, Math.round(fakeRate * 0.5 + unknownRate * 0.2 + volumeWeight));
        return { source, risk: score, volume: count };
      })
      .sort((a, b) => b.risk - a.risk)
      .slice(0, 10)
      .map((item, index) => ({
        ...item,
        sourceLabel: `SRC-${index + 1}`,
      }));
  }, [summary, totals]);

  return (
    <div className="mx-auto w-full max-w-7xl px-6 pb-10">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Big Data Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Multi-weighted intelligence metrics from ChromaDB and model outputs.</p>
        </div>
      </div>

      {loading ? <p className="text-sm text-slate-500">Loading metrics...</p> : null}
      {error ? <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

      {!loading && !error && summary ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <CommandCard title="Total Verifications" value={`${summary.total_articles}`} subtitle="Records in vector storage" icon={Sigma} />
            <CommandCard title="Trust Rate" value={`${totals.trustRate}%`} subtitle="Real vs Fake confidence ratio" icon={ShieldCheck} />
            <CommandCard title="Fake Signals" value={`${totals.fake}`} subtitle="High-risk detection volume" icon={AlertTriangle} />
            <CommandCard title="Real Signals" value={`${totals.real}`} subtitle="Trusted detection volume" icon={CheckCircle2} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
            <section className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-lg backdrop-blur-xl">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">Trust Distribution</h2>
              <div className="h-72">
                {distributionData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={distributionData} dataKey="value" nameKey="name" outerRadius={104} label />
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-slate-500">No distribution data available.</p>
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-white/40 bg-white/60 p-6 shadow-lg backdrop-blur-xl">
              <h2 className="mb-4 text-lg font-semibold text-slate-900">Risk Heatmap By Source</h2>
              <div className="h-72">
                {heatmapData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={heatmapData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="sourceLabel" interval={0} />
                      <YAxis domain={[0, 100]} />
                      <Tooltip
                        labelFormatter={(_, payload) => {
                          const row = payload?.[0]?.payload as { source?: string; sourceLabel?: string } | undefined;
                          if (!row) return "";
                          return `${row.sourceLabel}: ${row.source}`;
                        }}
                        formatter={(value: string | number) => [`${value}`, "Risk Score"]}
                      />
                      <Bar dataKey="risk" radius={[8, 8, 0, 0]}>
                        {heatmapData.map((entry) => (
                          <Cell key={`${entry.source}-${entry.sourceLabel}`} fill={toRiskColor(entry.risk)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-slate-500">No source data available.</p>
                )}
              </div>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
