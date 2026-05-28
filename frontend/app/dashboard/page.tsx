"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { API_URL, apiFetch } from "../../lib/api";

interface Metrics {
  total_pipeline_liquidity?: number;
  predicted_revenue_leakage?: number;
  total_claims?: number;
  high_risk_count?: number;
  avg_denial_probability?: number;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics>({});
  const [loading, setLoading] = useState(true);
  const [recentClaims, setRecentClaims] = useState<any[]>([]);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [m, q] = await Promise.all([
        apiFetch("/api/dashboard-metrics"),
        apiFetch("/api/priority-queue?mode=expected_loss"),
      ]);
      setMetrics(m);
      setRecentClaims((q.claims || []).slice(0, 5));
    } catch {
      toast.error("Could not load dashboard", {
        description: "Ensure backend is running on port 8000",
      });
    }
    setLoading(false);
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const launchDemo = async () => {
    try {
      const data = await apiFetch("/api/seed-demo", { method: "POST" });
      toast.success(`Demo Ready: ${data.seeded} Claims Loaded`, {
        description: `$${Math.round(data.total_revenue_at_risk).toLocaleString()} revenue at risk`,
      });
      await loadDashboard();
      setTimeout(() => {
        window.location.href = "/queue?mode=treasury";
      }, 800);
    } catch {
      toast.error("Could not connect to backend");
    }
  };

  const kpis = [
    {
      label: "Pipeline Liquidity",
      value: metrics.total_pipeline_liquidity
        ? `$${metrics.total_pipeline_liquidity.toLocaleString()}`
        : "—",
    },
    {
      label: "Revenue at Risk",
      value: metrics.predicted_revenue_leakage
        ? `$${metrics.predicted_revenue_leakage.toLocaleString()}`
        : "—",
    },
    {
      label: "Claims Monitored",
      value: metrics.total_claims ?? "—",
    },
    {
      label: "High-Risk Claims",
      value: metrics.high_risk_count ?? "—",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-[var(--text-muted)] mt-1">
            Pre-submission revenue protection command center
          </p>
        </div>
        <button onClick={launchDemo} className="btn btn-primary">
          Load Pitch Demo
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {loading
          ? [1, 2, 3, 4].map((i) => (
              <div key={i} className="card p-5 h-24 skeleton rounded-3xl" />
            ))
          : kpis.map((kpi, i) => (
              <motion.div
                key={kpi.label}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="card p-5"
              >
                <div className="text-xs text-[var(--text-muted)] uppercase tracking-wider">
                  {kpi.label}
                </div>
                <div className="text-3xl font-semibold tabular-nums mt-1">{kpi.value}</div>
              </motion.div>
            ))}
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {[
          { href: "/queue", title: "Claims Queue", desc: "Bounded knapsack priority worklist" },
          { href: "/studio", title: "Agent Studio", desc: "Live ambient auditing terminal" },
          { href: "/reports", title: "Reports", desc: "Executive liquidity analytics" },
        ].map((card) => (
          <a
            key={card.href}
            href={card.href}
            className="card p-6 hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-semibold text-lg">{card.title}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">{card.desc}</div>
          </a>
        ))}
      </div>

      <div className="card p-6">
        <div className="font-semibold mb-4">Top Priority Claims</div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 skeleton rounded-xl" />
            ))}
          </div>
        ) : recentClaims.length === 0 ? (
          <div className="text-center py-8 text-[var(--text-muted)]">
            No claims yet. Click <strong>Load Pitch Demo</strong> to get started.
          </div>
        ) : (
          <div className="space-y-2">
            {recentClaims.map((c) => (
              <div
                key={c.claim_id}
                className="flex justify-between items-center p-3 rounded-xl bg-[var(--bg)] border border-[var(--border)]"
              >
                <div>
                  <div className="font-mono text-xs">{c.claim_id}</div>
                  <div className="text-sm">${c.claim_value_usd?.toLocaleString()}</div>
                </div>
                <div className="text-right">
                  <span className={`risk-pill risk-${c.risk_level}`}>{c.risk_level}</span>
                  <div className="text-sm font-semibold tabular-nums mt-0.5">
                    ${c.expected_loss_usd?.toLocaleString()} at risk
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
