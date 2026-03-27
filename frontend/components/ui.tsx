"use client";

import {
  useEffect,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/components/cn";

export function PageShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("mx-auto w-full max-w-7xl px-6 pb-12", className)}>{children}</div>;
}

export function SectionHeader({
  title,
  description,
  action,
  className,
  eyebrow,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  eyebrow?: string;
}) {
  return (
    <div className={cn("mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{eyebrow}</p>
        ) : null}
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {description ? <p className="max-w-3xl text-sm text-slate-600">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function DashboardCard({
  children,
  className,
  hover = false,
  ...props
}: HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  hover?: boolean;
}) {
  return (
    <section
      className={cn(
        "group relative rounded-2xl border border-slate-200 bg-white p-6 shadow-sm backdrop-blur-xl supports-[backdrop-filter]:bg-white/78",
        "before:pointer-events-none before:absolute before:inset-0 before:rounded-[inherit] before:bg-[linear-gradient(180deg,rgba(255,255,255,0.7),rgba(255,255,255,0))] before:opacity-80",
        hover &&
          "transition-all duration-200 ease-out hover:-translate-y-1 hover:border-slate-300 hover:shadow-[0_18px_42px_-24px_rgba(15,23,42,0.25)]",
        className
      )}
      {...props}
    >
      {children}
    </section>
  );
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  className,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon?: LucideIcon;
  className?: string;
}) {
  const highlight = useMemo(() => resolveMetricHighlight(title, value), [title, value]);

  return (
    <DashboardCard hover className={cn("relative overflow-hidden", className)}>
      <div className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-slate-200 via-white to-slate-200" />
      {highlight ? (
        <div
          className={cn(
            "pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full blur-3xl transition-opacity duration-200 ease-out",
            highlight
          )}
        />
      ) : null}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-900">{title}</p>
          <AnimatedMetricValue value={value} />
          {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
        </div>
        {Icon ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5 text-slate-600 shadow-sm transition-all duration-200 ease-out group-hover:scale-105">
            <Icon size={18} />
          </div>
        ) : null}
      </div>
    </DashboardCard>
  );
}

export function ChartContainer({
  title,
  description,
  action,
  children,
  className,
  contentClassName,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <DashboardCard className={className}>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          {description ? <p className="text-sm text-slate-600">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className={cn("h-80", contentClassName)}>{children}</div>
    </DashboardCard>
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "success" | "danger";
}) {
  const variants = {
    primary:
      "bg-slate-900 text-white hover:bg-slate-800 focus-visible:outline-slate-900/20",
    secondary:
      "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus-visible:outline-slate-200",
    success:
      "border border-green-200 bg-green-50 text-green-700 hover:border-green-300 hover:bg-green-100 focus-visible:outline-green-200",
    danger:
      "border border-red-200 bg-red-50 text-red-700 hover:border-red-300 hover:bg-red-100 focus-visible:outline-red-200",
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium shadow-sm transition-all duration-200 ease-out active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export function Skeleton({
  className,
}: {
  className?: string;
}) {
  return <div className={cn("animate-pulse rounded-lg bg-slate-200", className)} aria-hidden="true" />;
}

export function MetricCardSkeleton() {
  return (
    <DashboardCard className="overflow-hidden">
      <div className="space-y-4">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-9 w-28" />
        <Skeleton className="h-3 w-36" />
      </div>
    </DashboardCard>
  );
}

export function ChartSkeleton() {
  return (
    <div className="flex h-full flex-col justify-between">
      <div className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-48" />
      </div>
      <div className="mt-8 grid h-full grid-cols-6 items-end gap-3">
        <Skeleton className="h-16" />
        <Skeleton className="h-28" />
        <Skeleton className="h-20" />
        <Skeleton className="h-36" />
        <Skeleton className="h-24" />
        <Skeleton className="h-32" />
      </div>
    </div>
  );
}

export function ListItemSkeleton() {
  return (
    <DashboardCard className="p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="w-full max-w-xl space-y-3">
          <Skeleton className="h-4 w-4/5" />
          <Skeleton className="h-3 w-2/5" />
          <Skeleton className="h-3 w-full" />
        </div>
        <Skeleton className="h-4 w-28" />
      </div>
    </DashboardCard>
  );
}

export function Notice({
  tone = "default",
  children,
  className,
}: {
  tone?: "default" | "danger" | "success" | "warning";
  children: ReactNode;
  className?: string;
}) {
  const tones = {
    default: "border-slate-200 bg-slate-50 text-slate-600",
    danger: "border-red-200 bg-red-50 text-red-600",
    success: "border-green-200 bg-green-50 text-green-600",
    warning: "border-amber-200 bg-amber-50 text-amber-600",
  };

  return (
    <div className={cn("rounded-2xl border px-4 py-3 text-sm", tones[tone], className)}>
      {children}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title = "No data available yet",
  description,
  className,
}: {
  icon: LucideIcon;
  title?: string;
  description?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex h-full min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-6 text-center shadow-inner",
        className
      )}
    >
      <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-3 text-slate-400 shadow-sm">
        <Icon size={18} />
      </div>
      <p className="text-sm font-medium text-slate-900">{title}</p>
      {description ? <p className="mt-2 max-w-sm text-sm text-slate-500">{description}</p> : null}
    </div>
  );
}

export function Badge({
  tone = "default",
  children,
  className,
}: {
  tone?: "default" | "info" | "success" | "danger" | "warning";
  children: ReactNode;
  className?: string;
}) {
  const tones = {
    default: "border-slate-200 bg-white/90 text-slate-600 supports-[backdrop-filter]:bg-white/72",
    info: "border-sky-200 bg-sky-50 text-sky-700 supports-[backdrop-filter]:bg-sky-50/85",
    success: "border-green-200 bg-green-50 text-green-600 supports-[backdrop-filter]:bg-green-50/85",
    danger: "border-red-200 bg-red-50 text-red-600 supports-[backdrop-filter]:bg-red-50/85",
    warning: "border-amber-200 bg-amber-50 text-amber-700 supports-[backdrop-filter]:bg-amber-50/85",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium shadow-sm",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

function AnimatedMetricValue({ value }: { value: string }) {
  const [displayValue, setDisplayValue] = useState<string | null>(null);
  const parsed = useMemo(() => parseAnimatedMetric(value), [value]);

  useEffect(() => {
    if (!parsed) return;

    let frame = 0;
    frame = requestAnimationFrame((startTimestamp) => {
      const duration = 650;

      const step = (timestamp: number) => {
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const nextValue = parsed.decimals
          ? (parsed.value * eased).toFixed(parsed.decimals)
          : Math.round(parsed.value * eased).toString();

        setDisplayValue(`${parsed.prefix}${nextValue}${parsed.suffix}`);

        if (progress < 1) {
          frame = requestAnimationFrame(step);
        }
      };

      step(startTimestamp);
    });

    return () => cancelAnimationFrame(frame);
  }, [parsed]);

  return <p className="text-3xl font-semibold tracking-tight text-slate-900">{parsed ? displayValue ?? value : value}</p>;
}

function parseAnimatedMetric(value: string) {
  if (value.includes(":")) return null;
  const match = value.match(/^([^0-9-]*)(-?\d+(?:\.\d+)?)(.*)$/);
  if (!match) return null;

  const [, prefix, rawNumber, suffix] = match;
  if (suffix.includes(":")) return null;

  const numericValue = Number(rawNumber);
  if (!Number.isFinite(numericValue)) return null;

  return {
    prefix,
    value: numericValue,
    suffix,
    decimals: rawNumber.includes(".") ? rawNumber.split(".")[1].length : 0,
  };
}

function resolveMetricHighlight(title: string, value: string) {
  const token = `${title} ${value}`.toLowerCase();
  if (token.includes("fake") || token.includes("risk")) return "bg-red-100/70";
  if (token.includes("real") || token.includes("trust") || token.includes("success")) return "bg-emerald-100/70";
  if (token.includes("%")) return "bg-sky-100/70";
  return "bg-slate-100/70";
}
