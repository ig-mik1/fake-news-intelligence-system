"use client";

import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, CheckCircle2, PieChart as PieChartIcon, ShieldCheck, Sigma } from "lucide-react";
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
import {
  Badge,
  ChartContainer,
  ChartSkeleton,
  EmptyState,
  MetricCardSkeleton,
  Notice,
  PageShell,
  SectionHeader,
} from "@/components/ui";
import { getDashboardSummary, type DashboardSummaryResponse } from "@/lib/api";

const CHART_TOOLTIP_STYLE = {
  borderRadius: "16px",
  border: "1px solid #e2e8f0",
  backgroundColor: "rgba(255, 255, 255, 0.96)",
  boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
  padding: "10px 12px",
};

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
    const trustRate = pct(real, classified);
    return { fake, real, unknown, classified, trustRate };
  }, [summary]);

  const distributionData = useMemo(
    () =>
      [
        { name: "Real", value: totals.real, fill: "#16a34a" },
        { name: "Fake", value: totals.fake, fill: "#dc2626" },
        { name: "Unknown", value: totals.unknown, fill: "#64748b" },
      ].filter((item) => item.value > 0),
    [totals]
  );

  const heatmapData = useMemo(() => {
    if (!summary) return [];
    const entries = Object.entries(summary.source_distribution);
    if (!entries.length) return [];

    const maxCount = Math.max(...entries.map(([, count]) => count), 1);
    const totalArticles = Math.max(summary.total_articles, 1);
    const fakeRate = pct(totals.fake, totalArticles);
    const unknownRate = pct(totals.unknown, totalArticles);

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
    <PageShell>
      <SectionHeader
        title="Big Data Dashboard"
        description="Multi-weighted intelligence metrics from ChromaDB and model outputs, presented with a cleaner analytics hierarchy."
        action={
          <Badge>
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Sample size {summary?.sample_size ?? 60}
          </Badge>
        }
      />

      {loading ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <MetricCardSkeleton key={index} />
            ))}
          </div>
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ChartContainer title="Trust Distribution" description="Loading chart..." contentClassName="h-72 sm:h-80">
              <ChartSkeleton />
            </ChartContainer>
            <ChartContainer title="Risk Heatmap By Source" description="Loading chart..." contentClassName="h-72 sm:h-80">
              <ChartSkeleton />
            </ChartContainer>
          </div>
        </>
      ) : null}
      {error ? <Notice tone="danger">{error}</Notice> : null}

      {!loading && !error && summary ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <CommandCard title="Total Verifications" value={`${summary.total_articles}`} subtitle="Records in vector storage" icon={Sigma} />
            <CommandCard title="Trust Rate" value={`${totals.trustRate}%`} subtitle="Real vs Fake confidence ratio" icon={ShieldCheck} />
            <CommandCard title="Fake Signals" value={`${totals.fake}`} subtitle="High-risk detection volume" icon={AlertTriangle} />
            <CommandCard title="Real Signals" value={`${totals.real}`} subtitle="Trusted detection volume" icon={CheckCircle2} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ChartContainer
              title="Trust Distribution"
              description="Classification mix across the latest dashboard sample."
              action={summary.estimated_from_sample ? <Badge>Estimated sample</Badge> : <Badge>Live summary</Badge>}
              contentClassName="h-72 sm:h-80"
            >
              <div className="h-full">
                {distributionData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={distributionData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={68}
                        outerRadius={104}
                        paddingAngle={3}
                        stroke="#f8fafc"
                        strokeWidth={4}
                        isAnimationActive
                        animationDuration={500}
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${Math.round((percent ?? 0) * 100)}%`}
                      />
                      <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(value?: ValueType) => [`${value ?? 0}`, "Articles"]} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState
                    icon={PieChartIcon}
                    title="No data available yet"
                    description="Distribution will appear once verified articles are available."
                  />
                )}
              </div>
            </ChartContainer>

            <ChartContainer
              title="Risk Heatmap By Source"
              description="The riskiest active sources based on volume, fake rate, and unknown classifications."
              contentClassName="h-72 sm:h-80"
            >
              <div className="h-full">
                {heatmapData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={heatmapData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="#e2e8f0" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="sourceLabel"
                        interval={0}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748b", fontSize: 12 }}
                      />
                      <YAxis
                        domain={[0, 100]}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748b", fontSize: 12 }}
                      />
                      <Tooltip
                        contentStyle={CHART_TOOLTIP_STYLE}
                        labelFormatter={(_, payload) => {
                          const row = payload?.[0]?.payload as
                            | { source?: string; sourceLabel?: string }
                            | undefined;

                          if (!row) return "";
                          return `${row.sourceLabel}: ${row.source}`;
                        }}
                        formatter={(value?: ValueType, name?: NameType) => [`${value ?? 0}%`, String(name ?? "")]}
                      />
                      <Bar dataKey="risk" name="Risk score" radius={[10, 10, 0, 0]} barSize={34} animationDuration={500}>
                        {heatmapData.map((entry) => (
                          <Cell key={`${entry.source}-${entry.sourceLabel}`} fill={toRiskColor(entry.risk)} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState
                    icon={BarChart3}
                    title="No data available yet"
                    description="Source risk scores will render after the dashboard receives source distribution data."
                  />
                )}
              </div>
            </ChartContainer>
          </div>
        </>
      ) : null}
    </PageShell>
  );
}
