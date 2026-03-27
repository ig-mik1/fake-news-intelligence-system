"use client";

import { Search } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/components/cn";

const LINKS = [
  { label: "Home", href: "/" },
  { label: "Dashboard", href: "/dashboard" },
  { label: "Verify", href: "/verify" },
  { label: "Monitoring", href: "/monitoring" },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/80 bg-slate-50/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-3 text-slate-900 transition hover:opacity-90">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
            <span className="text-sm font-semibold tracking-tight">FN</span>
          </span>
          <span className="hidden sm:block">
            <span className="block text-sm font-semibold tracking-tight">Fake News Intelligence</span>
            <span className="block text-xs text-slate-500">Analytics workspace</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-white/90 p-1 shadow-sm supports-[backdrop-filter]:bg-white/72">
          {LINKS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-xl px-3.5 py-2 text-sm font-medium transition duration-200",
                  active
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent("open-command-palette"))}
          className="hidden items-center gap-2 rounded-2xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-500 shadow-sm transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-slate-300 hover:text-slate-900 md:inline-flex"
        >
          <Search size={14} />
          <span>Search</span>
          <span className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-400">Ctrl/Cmd K</span>
        </button>
      </div>
    </header>
  );
}
