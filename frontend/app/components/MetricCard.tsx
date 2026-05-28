"use client";

interface MetricCardProps {
  label: string;
  value: string;
  change?: string;
  icon?: string;
  highlight?: boolean;
}

export function MetricCard({ label, value, change, highlight }: MetricCardProps) {
  return (
    <div className={`card p-6 ${highlight ? 'ring-1 ring-[var(--accent)]/30' : ''}`}>
      <div className="text-sm text-[var(--text-muted)] font-medium tracking-widest">{label}</div>
      <div className="metric-value text-4xl font-semibold tabular-nums tracking-[-2.5px] mt-2">{value}</div>
      {change && <div className="text-xs text-[var(--accent)] mt-3 font-medium">{change}</div>}
    </div>
  );
}