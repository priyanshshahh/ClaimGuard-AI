"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { apiFetch } from "../../lib/api";
import { DEMO_MODE } from "../../lib/demo";
import { EmptyState, ErrorBanner, PageHeader, Skeleton } from "../components/ui";

interface Metrics {
  total_pipeline_liquidity?: number;
  predicted_revenue_leakage?: number;
  total_claims?: number;
  high_risk_count?: number;
}

interface QueueClaim {
  claim_id: string;
  claim_value_usd?: number;
  risk_level?: string;
  expected_loss_usd?: number;
}

/** Dashboard — /dashboard. Calls /api/dashboard-metrics + /api/priority-queue. */
export default function DashboardPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentClaims, setRecentClaims] = useState<QueueClaim[]>([]);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, q] = await Promise.all([
        apiFetch<Metrics>("/api/dashboard-metrics"),
        apiFetch<{ claims?: QueueClaim[] }>("/api/priority-queue?mode=expected_loss"),
      ]);
      setMetrics(m);
      setRecentClaims((q.claims || []).slice(0, 5));
    } catch {
      setError("Could not load dashboard. Ensure the API is running on port 8000.");
      toast.error("Could not load dashboard");
    }
    setLoading(false);
  };

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) void loadDashboard();
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const launchDemo = async () => {
    try {
      const data = await apiFetch<{ seeded: number; total_revenue_at_risk: number }>(
        "/api/seed-demo",
        { method: "POST" },
      );
      toast.success(`Demo ready: ${data.seeded} claims`);
      await loadDashboard();
      setTimeout(() => {
        router.push("/queue?mode=treasury");
      }, 600);
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
    { label: "Claims Monitored", value: metrics.total_claims ?? "—" },
    { label: "High-Risk Claims", value: metrics.high_risk_count ?? "—" },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <PageHeader
        title="Dashboard"
        description="Pre-submission revenue protection overview"
        actions={
          DEMO_MODE ? (
            <button type="button" onClick={launchDemo} className="btn btn-primary">
              Load demo claims
            </button>
          ) : (
            <Link href="/queue" className="btn btn-primary">
              Open claims queue
            </Link>
          )
        }
      />

      {error ? <ErrorBanner message={error} onRetry={loadDashboard} /> : null}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {loading
          ? [1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)
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

      {!loading && (metrics.high_risk_count ?? 0) > 0 ? (
        <div className="flex flex-wrap items-center gap-2 text-sm rounded-2xl border border-[var(--accent)]/20 bg-[var(--accent)]/5 px-4 py-3">
          <span className="font-medium text-[var(--text)]">Next:</span>
          <span className="text-[var(--text-muted)]">
            {metrics.high_risk_count} high-risk{" "}
            {metrics.high_risk_count === 1 ? "claim needs" : "claims need"} review —
          </span>
          <Link
            href="/queue?mode=expected_loss"
            className="font-medium text-[var(--accent)] hover:underline"
          >
            open them in the Queue →
          </Link>
        </div>
      ) : null}

      <div className="grid md:grid-cols-3 gap-4">
        {[
          { href: "/queue", title: "Claims Queue", desc: "Bounded knapsack priority worklist" },
          { href: "/studio", title: "Agent Studio", desc: "Note analysis and appeals" },
          { href: "/reports", title: "Reports", desc: "Executive liquidity analytics" },
        ].map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="card p-6 hover:border-[var(--primary)] transition-colors"
          >
            <div className="font-semibold text-lg">{card.title}</div>
            <div className="text-sm text-[var(--text-muted)] mt-1">{card.desc}</div>
          </Link>
        ))}
      </div>

      <div className="card p-6">
        <div className="font-semibold mb-4">Top priority claims</div>
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : recentClaims.length === 0 ? (
          <EmptyState
            title="No claims yet"
            description={
              DEMO_MODE
                ? "Load demo claims to populate the queue, or analyze a new claim in Agent Studio."
                : "Analyze a claim in Agent Studio or open the queue to get started."
            }
            action={
              DEMO_MODE ? (
                <button type="button" onClick={launchDemo} className="btn btn-primary">
                  Load demo claims
                </button>
              ) : (
                <Link href="/studio" className="btn btn-primary">
                  Open Agent Studio
                </Link>
              )
            }
          />
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
