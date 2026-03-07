"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Clock3, Newspaper, Radio, RefreshCcw } from "lucide-react";

import CommandCard from "@/components/command-card";
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
    <div className="max-w-6xl mx-auto py-12 px-6">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Live Monitoring Stream</h1>
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-green-50 text-green-700 rounded-full text-xs font-bold">
          <span className="w-2 h-2 rounded-full bg-green-600 animate-pulse" />
          REAL-TIME
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
        <CommandCard title="Streamed Items" value={`${items.length}`} subtitle="Loaded from /api/monitoring/latest" icon={Newspaper} />
        <CommandCard title="Active Sources" value={`${activeSources}`} subtitle="Reported by backend stream" icon={Radio} />
        <CommandCard title="Last Sync" value={lastSync} subtitle={`Auto-refresh every ${REFRESH_MS / 1000}s`} icon={RefreshCcw} />
      </div>

      {loading ? <p className="text-slate-500">Loading latest stream...</p> : null}
      {error ? <p className="text-red-600 mb-4">{error}</p> : null}

      {!loading && !error ? (
        <div className="space-y-3">
          {items.length === 0 ? (
            <p className="text-slate-500">No items found in vector storage yet.</p>
          ) : null}

          {items.map((item, index) => (
            <motion.div
              key={`${item.id}-${index}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.02 }}
              className="bg-white border border-slate-100 rounded-xl p-4 shadow-sm"
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <h3 className="text-sm md:text-base font-semibold text-slate-900">{item.title}</h3>
                  <p className="text-xs text-slate-500 mt-1 uppercase tracking-wide">
                    Source: {item.source} | Platform: {item.platform}
                  </p>
                  {item.url ? (
                    <a className="text-xs text-blue-600 hover:underline break-all" href={item.url} target="_blank" rel="noreferrer">
                      {item.url}
                    </a>
                  ) : null}
                </div>
                <div className="inline-flex items-center gap-2 text-xs text-slate-500">
                  <Clock3 size={14} />
                  {formatTime(item.ingested_at)}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function resolveActiveSources(response: MonitoringLatestResponse): number {
  if (typeof response.active_sources === "number") {
    return response.active_sources;
  }
  const sourceSet = new Set((response.items || []).map((item) => item.source));
  return sourceSet.size;
}
