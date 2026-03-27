// frontend/app/page.tsx
"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Activity, ArrowRight, ShieldCheck, Waves } from "lucide-react";

import { Badge, Button, DashboardCard, MetricCard, PageShell } from "@/components/ui";

export default function Home() {
  const router = useRouter();

  return (
    <PageShell className="pb-16">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(20rem,0.9fr)]">
        <motion.section initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}>
          <DashboardCard className="p-8 md:p-10" hover>
            <Badge className="border-sky-200 bg-sky-50/90 text-sky-700 supports-[backdrop-filter]:bg-sky-50/70">
              <span className="h-2 w-2 rounded-full bg-sky-500 animate-pulse" />
              AI news intelligence platform
            </Badge>

            <div className="mt-8 max-w-2xl space-y-4">
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                A cleaner verification workspace for trust scoring, evidence review, and live monitoring.
              </h1>
              <p className="text-sm text-slate-600">
                Review suspicious headlines, inspect corroborating sources, and monitor ingestion activity from one
                consistent analytics dashboard.
              </p>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Button onClick={() => router.push("/verify")}>
                Start Verification
                <ArrowRight size={16} />
              </Button>
              <Button variant="secondary" onClick={() => router.push("/dashboard")}>
                Open Dashboard
              </Button>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-900">Cross-check faster</p>
                <p className="mt-2 text-sm text-slate-600">
                  Pull ML confidence, source quality, and evidence consensus into one decision flow.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-900">Read the signal</p>
                <p className="mt-2 text-sm text-slate-600">
                  Use muted charts and structured metrics to spot misinformation patterns quickly.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-900">Stay operational</p>
                <p className="mt-2 text-sm text-slate-600">
                  Monitor ingestion freshness and source activity without leaving the app shell.
                </p>
              </div>
            </div>
          </DashboardCard>
        </motion.section>

        <motion.aside
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="grid gap-4"
        >
          <MetricCard
            title="Verification workflow"
            value="3-step"
            subtitle="Analyze headline, inspect evidence, collect human feedback"
            icon={ShieldCheck}
          />
          <MetricCard
            title="Monitoring cadence"
            value="30s"
            subtitle="Live stream refresh interval across source ingestion"
            icon={Activity}
          />
          <MetricCard
            title="Dashboard posture"
            value="Clean"
            subtitle="Unified cards, readable charts, and softer visual hierarchy"
            icon={Waves}
          />
        </motion.aside>
      </div>
    </PageShell>
  );
}
