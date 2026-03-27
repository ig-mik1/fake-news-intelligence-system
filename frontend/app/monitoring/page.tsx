"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Clock3, Newspaper, Radio, RefreshCcw, SearchX } from "lucide-react";

import CommandCard from "@/components/command-card";
import {
  Badge,
  DashboardCard,
  EmptyState,
  ListItemSkeleton,
  MetricCardSkeleton,
  Notice,
  PageShell,
  SectionHeader,
} from "@/components/ui";
import { getMonitoringLatest, type MonitoringItem, type MonitoringLatestResponse } from "@/lib/api";

const REFRESH_MS = 30000;

function formatTime(input: string): string {
  const parsed = new Date(input);
  if (Number.isNaN(parsed.getTime())) return input;
  return parsed.toLocaleString();
}

export default function MonitoringPage() {
  const [items, setItems] = useState<MonitoringItem[]>([]);
  const [activeSources, setActiveSources] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<string>("-");

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        if (active) {
          setError(null);
        }
        const response = await getMonitoringLatest(25);
        if (!active) return;
        if (response.status !== "ok") {
          setItems([]);
          setActiveSources(0);
          setError(response.error || "Monitoring service is degraded. Try again shortly.");
          return;
        }
        setItems(response.items || []);
        setActiveSources(resolveActiveSources(response));
        setLastSync(new Date().toLocaleTimeString());
      } catch (err) {
        if (active) {
          const message = err instanceof Error ? err.message : "Could not load latest monitoring stream.";
          setError(message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void load();
    const timer = setInterval(() => {
      void load();
    }, REFRESH_MS);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <PageShell>
      <SectionHeader
        title="Live Monitoring Stream"
        description="Track the freshest ingested records, active sources, and sync cadence in a consistent analyst feed."
        action={
          <Badge className="border-green-200 bg-green-50 text-green-600 supports-[backdrop-filter]:bg-green-50/80">
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            Real-time
          </Badge>
        }
      />

      {loading ? (
        <>
          <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <MetricCardSkeleton key={index} />
            ))}
          </div>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, index) => (
              <ListItemSkeleton key={index} />
            ))}
          </div>
        </>
      ) : (
        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          <CommandCard title="Streamed Items" value={`${items.length}`} subtitle="Loaded from /api/monitoring/latest" icon={Newspaper} />
          <CommandCard title="Active Sources" value={`${activeSources}`} subtitle="Reported by backend stream" icon={Radio} />
          <CommandCard title="Last Sync" value={lastSync} subtitle={`Auto-refresh every ${REFRESH_MS / 1000}s`} icon={RefreshCcw} />
        </div>
      )}

      {error ? <Notice tone="danger" className="mb-4">{error}</Notice> : null}

      {!loading && !error ? (
        <div className="space-y-3">
          {items.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title="No data available yet"
              description="The monitoring stream will populate once new items are ingested into vector storage."
            />
          ) : null}

          {items.map((item, index) => (
            <motion.div
              key={`${item.id}-${index}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.02 }}
            >
              <DashboardCard hover className="p-5">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="space-y-2">
                    <h2 className="text-sm font-medium text-slate-900 md:text-base">{item.title}</h2>
                    <p className="text-xs text-slate-500">
                      Source: {item.source} | Platform: {item.platform}
                    </p>
                    {item.url ? (
                      <a
                        className="block break-all text-sm text-slate-600 transition hover:text-slate-900 hover:underline"
                        href={item.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {item.url}
                      </a>
                    ) : null}
                  </div>
                  <div className="inline-flex items-center gap-2 text-xs text-slate-500">
                    <Clock3 size={14} />
                    {formatTime(item.ingested_at)}
                  </div>
                </div>
              </DashboardCard>
            </motion.div>
          ))}
        </div>
      ) : null}
    </PageShell>
  );
}

function resolveActiveSources(response: MonitoringLatestResponse): number {
  if (typeof response.active_sources === "number") {
    return response.active_sources;
  }
  const sourceSet = new Set((response.items || []).map((item) => item.source));
  return sourceSet.size;
}
