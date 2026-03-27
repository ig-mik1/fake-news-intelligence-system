"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Command, Home, LayoutDashboard, MonitorPlay, Search, Sparkles, ShieldCheck } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@/components/cn";

type PaletteItem = {
  id: string;
  label: string;
  hint: string;
  icon: typeof Home;
  keywords: string;
  perform: () => void;
};

export default function CommandPalette() {
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const closePalette = () => {
    setOpen(false);
    setQuery("");
    setActiveIndex(0);
  };

  const togglePalette = () => {
    setOpen((current) => {
      const next = !current;
      if (!next) {
        setQuery("");
        setActiveIndex(0);
      }
      return next;
    });
  };

  useEffect(() => {
    const handleOpen = () => setOpen(true);
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        togglePalette();
      }
      if (event.key === "Escape") {
        closePalette();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("open-command-palette", handleOpen);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("open-command-palette", handleOpen);
      };
    }, []);

  const items = useMemo<PaletteItem[]>(
    () => [
      {
        id: "home",
        label: "Go to Home",
        hint: "Landing overview",
        icon: Home,
        keywords: "home landing overview",
        perform: () => router.push("/"),
      },
      {
        id: "dashboard",
        label: "Open Dashboard",
        hint: "Metrics and charts",
        icon: LayoutDashboard,
        keywords: "dashboard analytics metrics charts",
        perform: () => router.push("/dashboard"),
      },
      {
        id: "verify",
        label: "Open Verify",
        hint: "Run AI verification",
        icon: ShieldCheck,
        keywords: "verify analysis trust evidence",
        perform: () => router.push("/verify"),
      },
      {
        id: "monitoring",
        label: "Open Monitoring",
        hint: "Latest ingestion stream",
        icon: MonitorPlay,
        keywords: "monitoring stream latest realtime",
        perform: () => router.push("/monitoring"),
      },
      {
        id: "focus-verify",
        label: "Focus Verification Input",
        hint: "Jump to the headline field",
        icon: Search,
        keywords: "focus verify input headline search",
        perform: () => {
          if (pathname !== "/verify") {
            router.push("/verify");
            setTimeout(() => window.dispatchEvent(new CustomEvent("focus-verify-input")), 220);
            setTimeout(() => window.dispatchEvent(new CustomEvent("focus-verify-input")), 520);
            return;
          }
          window.dispatchEvent(new CustomEvent("focus-verify-input"));
        },
      },
      {
        id: "refresh",
        label: "Refresh Current Page",
        hint: "Reload current data",
        icon: Sparkles,
        keywords: "refresh reload current page",
        perform: () => router.refresh(),
      },
    ],
    [pathname, router]
  );

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return items;
    return items.filter((item) =>
      `${item.label} ${item.hint} ${item.keywords}`.toLowerCase().includes(normalizedQuery)
    );
  }, [items, query]);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((current) => (filteredItems.length ? (current + 1) % filteredItems.length : 0));
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((current) =>
          filteredItems.length ? (current - 1 + filteredItems.length) % filteredItems.length : 0
        );
      }
      if (event.key === "Enter") {
        const selected = filteredItems[activeIndex];
        if (!selected) return;
        event.preventDefault();
        selected.perform();
        closePalette();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeIndex, filteredItems, open]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-900/12 px-4 pt-[12vh] backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          onClick={closePalette}
        >
          <motion.div
            className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 shadow-[0_30px_80px_-32px_rgba(15,23,42,0.35)] supports-[backdrop-filter]:bg-white/82"
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.985 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-slate-200 px-4 py-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-slate-500">
                <Command size={16} />
              </div>
              <input
                autoFocus
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setActiveIndex(0);
                }}
                placeholder="Search pages and actions..."
                className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
              />
              <span className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-500">
                Esc
              </span>
            </div>

            <div className="max-h-[24rem] overflow-y-auto p-2">
              {filteredItems.length ? (
                filteredItems.map((item, index) => {
                  const Icon = item.icon;
                  const active = index === activeIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => {
                        item.perform();
                        closePalette();
                      }}
                      className={cn(
                        "flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition-all duration-200 ease-out",
                        active ? "bg-slate-900 text-white shadow-sm" : "text-slate-700 hover:bg-slate-100"
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "rounded-xl border p-2 transition-all duration-200 ease-out",
                            active ? "border-white/20 bg-white/10 text-white" : "border-slate-200 bg-white text-slate-500"
                          )}
                        >
                          <Icon size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{item.label}</p>
                          <p className={cn("text-xs", active ? "text-slate-300" : "text-slate-500")}>{item.hint}</p>
                        </div>
                      </div>
                    </button>
                  );
                })
              ) : (
                <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
                  <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 p-3 text-slate-400">
                    <Search size={18} />
                  </div>
                  <p className="text-sm font-medium text-slate-900">No matching commands</p>
                  <p className="mt-2 text-sm text-slate-500">Try a page name like Dashboard, Verify, or Monitoring.</p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
              <span>Use arrow keys to navigate</span>
              <span>Press Enter to run</span>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
