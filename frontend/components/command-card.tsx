import type { LucideIcon } from "lucide-react";

interface CommandCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: LucideIcon;
}

export default function CommandCard({ title, value, subtitle, icon: Icon }: CommandCardProps) {
  return (
    <div className="p-6 bg-white border border-slate-100 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold">{title}</p>
          <p className="text-3xl font-bold text-slate-900 mt-2">{value}</p>
          {subtitle ? <p className="text-xs text-slate-500 mt-2">{subtitle}</p> : null}
        </div>
        {Icon ? (
          <div className="p-2 rounded-lg bg-slate-50 text-slate-700">
            <Icon size={18} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
