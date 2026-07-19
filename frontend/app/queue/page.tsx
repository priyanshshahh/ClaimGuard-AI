"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { NewClaimModal } from "../components/NewClaimModal";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch } from "../../lib/api";
import { EmptyState, ErrorBanner, PageHeader } from "../components/ui";

const fmtUsd = (n?: number) =>
  typeof n === "number" ? `$${n.toLocaleString()}` : "—";

interface Claim {
  claim_id: string;
  claim_value_usd?: number;
  denial_probability: number;
  risk_level: string;
  expected_loss_usd?: number;
  payer_days_to_pay?: number;
  cash_flow_urgency?: number;
  agent_correction_draft?: string;
  explanation?: string;
  recommended_action?: string;
  confidence?: number;
  documentation_complete?: number;
  clinical_justification_present?: number;
  procedure_mismatch_flag?: number;
  predicted_denial_codes?: string[];
  patient_chart_notes?: string;
  knapsack_selected?: boolean;
  expected_recovery_usd?: number;
  carc_code?: string | null;
  carc_group?: string | null;
  cert_category?: string | null;
  carc_reasons?: {
    carc_code: string;
    carc_desc: string;
    rarc_code: string;
    rarc_desc: string;
    group_code: string;
    cert_category: string;
  }[];
  top_drivers?: { label: string; contribution: number; direction: string }[];
}

type Mode = "expected_loss" | "expected_recovery" | "treasury";
type ScoreMode = "base" | "uplifted";

function getScoreMode(): ScoreMode {
  if (typeof window === "undefined") return "uplifted";
  const raw = localStorage.getItem("cg_score_mode");
  return raw === "base" ? "base" : "uplifted";
}

export default function ClaimsQueue() {
  const router = useRouter();
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Claim | null>(null);
  const [mode, setMode] = useState<Mode>("expected_loss");
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);

  const fetchQueue = async (newMode = mode) => {
    setLoading(true);
    try {
      const scoreMode = getScoreMode();
      const data = await apiFetch<{ claims?: Claim[] }>(
        `/api/priority-queue?mode=${newMode}&knapsack=true&score_mode=${scoreMode}`,
      );
      setClaims(data.claims || []);
      setError(null);
      setMode(newMode);

      const url = new URL(window.location.href);
      url.searchParams.set("mode", newMode);
      window.history.replaceState({}, "", url.toString());
    } catch {
      toast.error("Failed to load queue", {
        description: "Is the backend running on :8000?",
      });
      setClaims([]);
      setError(
        "Could not reach the backend. No live claim data is available.",
      );
    }
    setLoading(false);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlMode = params.get("mode") as Mode | null;
    const initialMode = urlMode || "expected_loss";
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setMode(initialMode);
      void fetchQueue(initialMode);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAccept = async (claim: Claim) => {
    try {
      await apiFetch("/api/resolve-claim", {
        method: "POST",
        body: JSON.stringify({ claim_id: claim.claim_id }),
      });
      toast.success(`Protected ${fmtUsd(claim.expected_loss_usd)}`, {
        description:
          "Claim marked resolved and persisted — it will stay out of the queue on refresh.",
      });
      setSelected(null);
      await fetchQueue();
    } catch {
      toast.error("Could not resolve claim", {
        description: "Backend did not persist the change.",
      });
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <PageHeader
        title="Auditor Worklist"
        description="Bounded knapsack queue — sorted by Expected Financial Loss (ELi = Vi × Pi)"
        actions={
          <>
            <label htmlFor="queue-mode" className="text-sm text-[var(--text-muted)] self-center">
              Rank by
            </label>
            <select
              id="queue-mode"
              value={mode}
              onChange={(e) => void fetchQueue(e.target.value as Mode)}
              className="px-3 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-xl text-sm"
            >
              <option value="expected_loss">Expected loss ($)</option>
              <option value="expected_recovery">Expected recovery ($)</option>
              <option value="treasury">Treasury / cash-flow urgency</option>
            </select>
            <button
              type="button"
              onClick={() => setShowNewClaimModal(true)}
              className="btn btn-primary"
            >
              New Claim
            </button>
          </>
        }
      />

      {mode === "treasury" ? (
        <div className="mb-6 p-3 bg-[var(--accent)]/5 border border-[var(--accent)]/20 rounded-2xl text-xs text-[var(--text-muted)] max-w-2xl">
          <strong>Treasury Mode Active:</strong> We multiply denial risk by payer
          slowness. A $40k claim from a 45-day payer can outrank a $70k claim from
          Medicare because the trapped cash hurts operations more. This is Dynamic
          Yield Management for healthcare revenue.
        </div>
      ) : null}

      {error ? (
        <ErrorBanner message={error} onRetry={() => void fetchQueue(mode)} />
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 card p-0 overflow-hidden">
          {loading ? (
            <div className="space-y-2 p-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-16 bg-[var(--bg)] rounded-2xl animate-pulse"
                />
              ))}
            </div>
          ) : claims.length === 0 ? (
            <EmptyState
              title="No claims in queue"
              description="Analyze a claim from Agent Studio or load demo data from the dashboard."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bg)] text-[var(--text-muted)] text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left p-3">Claim</th>
                    <th className="text-right p-3">Value</th>
                    <th className="text-center p-3">
                      P<sub>i</sub>
                    </th>
                    <th className="text-right p-3">
                      EL<sub>i</sub>
                    </th>
                    <th
                      className="text-right p-3"
                      title="Billed × P(denial) × assumed overturn rate"
                    >
                      Recovery
                    </th>
                    <th
                      className="text-center p-3"
                      title="Derived CARC denial reason + group code"
                    >
                      CARC
                    </th>
                    <th className="text-center p-3">Doc</th>
                    <th className="text-center p-3">Justify</th>
                    <th className="text-center p-3">Mismatch</th>
                  </tr>
                </thead>
                <tbody>
                  {claims.map((claim, idx) => (
                    <motion.tr
                      key={claim.claim_id || idx}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      onClick={() => setSelected(claim)}
                      className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--bg)] ${
                        selected?.claim_id === claim.claim_id ? "bg-[var(--bg)]" : ""
                      }`}
                    >
                      <td className="p-3">
                        <div className="font-mono text-xs">{claim.claim_id}</div>
                        {claim.knapsack_selected ? (
                          <span className="text-[10px] text-[var(--accent)] font-medium">
                            KNAPSACK TOP-K
                          </span>
                        ) : null}
                      </td>
                      <td className="p-3 text-right tabular-nums">
                        {fmtUsd(claim.claim_value_usd)}
                      </td>
                      <td className="p-3 text-center">
                        <span
                          className={`risk-pill risk-${claim.risk_level} text-[10px]`}
                        >
                          {(claim.denial_probability * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="p-3 text-right font-semibold tabular-nums">
                        {fmtUsd(claim.expected_loss_usd)}
                      </td>
                      <td className="p-3 text-right tabular-nums text-[var(--accent)]">
                        {fmtUsd(claim.expected_recovery_usd)}
                      </td>
                      <td className="p-3 text-center text-xs font-mono">
                        {claim.carc_code
                          ? `CARC ${claim.carc_code} · ${claim.carc_group}`
                          : "—"}
                      </td>
                      <td className="p-3 text-center">
                        <StatusBadge
                          ok={claim.documentation_complete !== 0}
                          okLabel="OK"
                          badLabel="Missing"
                          aria={
                            claim.documentation_complete !== 0
                              ? "Documentation complete"
                              : "Documentation missing"
                          }
                        />
                      </td>
                      <td className="p-3 text-center">
                        <StatusBadge
                          ok={claim.clinical_justification_present !== 0}
                          okLabel="OK"
                          badLabel="Missing"
                          aria={
                            claim.clinical_justification_present !== 0
                              ? "Clinical justification present"
                              : "Clinical justification missing"
                          }
                        />
                      </td>
                      <td className="p-3 text-center">
                        <StatusBadge
                          ok={claim.procedure_mismatch_flag !== 1}
                          okLabel="OK"
                          badLabel="Mismatch"
                          aria={
                            claim.procedure_mismatch_flag === 1
                              ? "Procedure code mismatch"
                              : "No procedure mismatch"
                          }
                        />
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="lg:col-span-5 card p-6 min-h-[420px]">
          {!selected ? (
            <div className="h-full flex items-center justify-center text-center text-[var(--text-muted)]">
              Select a claim from the queue to view agent analysis, confidence,
              and actions.
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={selected.claim_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono text-xs text-[var(--text-muted)]">
                      {selected.claim_id}
                    </div>
                    <div className="text-xl font-semibold">
                      {fmtUsd(selected.claim_value_usd)}
                    </div>
                  </div>
                  <div className={`risk-pill risk-${selected.risk_level}`}>
                    {selected.risk_level}
                  </div>
                </div>

                <div className="my-6 space-y-4 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[var(--bg)] p-3 rounded-xl border border-[var(--border)]">
                      <div className="text-[var(--text-muted)] text-[10px] tracking-widest">
                        EXPECTED LOSS
                      </div>
                      <div className="font-semibold tabular-nums">
                        {fmtUsd(selected.expected_loss_usd)}
                      </div>
                    </div>
                    <div className="bg-[var(--bg)] p-3 rounded-xl border border-[var(--border)]">
                      <div className="text-[var(--text-muted)] text-[10px] tracking-widest">
                        EXPECTED RECOVERY
                      </div>
                      <div className="font-semibold tabular-nums text-[var(--accent)]">
                        {fmtUsd(selected.expected_recovery_usd)}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)]">
                        billed × P(denial) × assumed overturn rate
                      </div>
                    </div>
                  </div>

                  {selected.carc_reasons && selected.carc_reasons.length > 0 ? (
                    <div>
                      <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">
                        DERIVED DENIAL REASON (CARC/RARC)
                      </div>
                      <div className="space-y-1">
                        {selected.carc_reasons.map((r, i) => (
                          <div
                            key={i}
                            className="text-xs bg-[var(--bg)] p-2 rounded-lg border border-[var(--border)]"
                          >
                            <span className="font-mono">
                              CARC {r.carc_code} · {r.group_code}
                            </span>{" "}
                            — {r.carc_desc}
                            <span className="block text-[var(--text-muted)]">
                              RARC {r.rarc_code}: {r.rarc_desc} · CERT:{" "}
                              {r.cert_category}
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-1">
                        Derived mapping — not a payer&apos;s actual remittance code.
                      </div>
                    </div>
                  ) : null}

                  {selected.top_drivers && selected.top_drivers.length > 0 ? (
                    <div>
                      <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">
                        TOP RISK DRIVERS (MODEL)
                      </div>
                      <ul className="space-y-0.5 text-xs">
                        {selected.top_drivers.map((d, i) => (
                          <li key={i} className="flex justify-between gap-2">
                            <span>{d.label}</span>
                            <span
                              className={
                                d.direction === "increases"
                                  ? "text-red-500"
                                  : "text-emerald-500"
                              }
                            >
                              {d.direction === "increases" ? "▲" : "▼"}{" "}
                              {d.contribution.toFixed(3)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  {selected.patient_chart_notes ? (
                    <div>
                      <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">
                        PATIENT CHART
                      </div>
                      <div className="bg-[var(--bg)] p-4 rounded-xl border border-[var(--border)] leading-relaxed text-xs max-h-32 overflow-auto">
                        {selected.patient_chart_notes}
                      </div>
                    </div>
                  ) : null}
                  <div>
                    <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">
                      AI REASONING
                    </div>
                    <div className="text-sm">
                      {selected.explanation || "No explanation available."}
                    </div>
                  </div>
                  <div>
                    <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">
                      AGENT CORRECTION DRAFT
                    </div>
                    <div className="bg-[var(--bg)] p-4 rounded-xl border border-[var(--border)] leading-relaxed">
                      {selected.agent_correction_draft ||
                        "High-quality correction will appear here after full analysis."}
                    </div>
                  </div>

                  {selected.confidence !== undefined ? (
                    <div className="text-xs">
                      Agent Confidence:{" "}
                      <span className="font-semibold">
                        {(selected.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  ) : null}
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    type="button"
                    onClick={() => void handleAccept(selected)}
                    className="btn btn-primary flex-1"
                  >
                    Resolve &amp; Protect
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      router.push(`/studio?claim=${encodeURIComponent(selected.claim_id)}`)
                    }
                    className="btn btn-ghost flex-1"
                  >
                    Open in Terminal
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelected(null)}
                    className="btn btn-ghost flex-1"
                  >
                    Close
                  </button>
                </div>
              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </div>

      <NewClaimModal
        isOpen={showNewClaimModal}
        onClose={() => setShowNewClaimModal(false)}
        onSuccess={(result) => {
          void fetchQueue();
          setSelected(result as unknown as Claim);
        }}
      />
    </div>
  );
}

function StatusBadge({
  ok,
  okLabel,
  badLabel,
  aria,
}: {
  ok: boolean;
  okLabel: string;
  badLabel: string;
  aria: string;
}) {
  return (
    <span
      role="status"
      aria-label={aria}
      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide ${
        ok
          ? "bg-[var(--accent)]/10 text-[var(--accent)]"
          : "bg-[var(--danger)]/10 text-[var(--danger)]"
      }`}
    >
      {ok ? okLabel : badLabel}
    </span>
  );
}
