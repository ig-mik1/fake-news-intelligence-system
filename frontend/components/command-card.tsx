import type { LucideIcon } from "lucide-react";

import { MetricCard } from "@/components/ui";

interface CommandCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon?: LucideIcon;
}

export default function CommandCard({ title, value, subtitle, icon: Icon }: CommandCardProps) {
  return <MetricCard title={title} value={value} subtitle={subtitle} icon={Icon} />;
}
