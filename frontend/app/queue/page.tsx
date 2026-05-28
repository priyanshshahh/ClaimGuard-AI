"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { NewClaimModal } from "../components/NewClaimModal";
import { motion, AnimatePresence } from "framer-motion";
import { API_URL } from "../../lib/api";

interface Claim {
  claim_id: string;
  claim_value_usd: number;
  denial_probability: number;
  risk_level: string;
  expected_loss_usd: number;
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
}

export default function ClaimsQueue() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Claim | null>(null);
  const [mode, setMode] = useState<"expected_loss" | "treasury">("expected_loss");
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);

  const fetchQueue = async (newMode = mode) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/priority-queue?mode=${newMode}&knapsack=true`);
      const data = await res.json();
      setClaims(data.claims || []);
      setMode(newMode as any);

      // Update URL so Treasury mode is shareable/bookmarkable
      const url = new URL(window.location.href);
      url.searchParams.set("mode", newMode);
      window.history.replaceState({}, "", url.toString());
    } catch (e) {
      toast.error("Failed to load queue", { description: "Is the backend running on :8000?" });
      setClaims([
        { claim_id: "CLM-ONC-3914", claim_value_usd: 187500, denial_probability: 0.42, risk_level: "MEDIUM", expected_loss_usd: 78750, payer_days_to_pay: 28, cash_flow_urgency: 1240 },
        { claim_id: "CLM-SPINE-5529", claim_value_usd: 67300, denial_probability: 0.68, risk_level: "HIGH", expected_loss_usd: 45764, payer_days_to_pay: 42, cash_flow_urgency: 1890 },
      ]);
    }
    setLoading(false);
  };

  useEffect(() => {
    // Support ?mode=treasury deep links (e.g. from landing page)
    const params = new URLSearchParams(window.location.search);
    const urlMode = params.get("mode") as "expected_loss" | "treasury" | null;
    const initialMode = urlMode || "expected_loss";
    setMode(initialMode);
    fetchQueue(initialMode);
  }, []);

  const handleAnalyze = async () => {
    const notes = prompt("Enter clinical notes for quick analysis (or cancel):");
    if (!notes) return;

    try {
      const payload = {
        claim_id: "QUICK-" + Date.now(),
        claim_value_usd: 35000,
        payer_id: "AETNA",
        icd_10_code: "M17.11",
        cpt_code: "27447",
        patient_chart_notes: notes
      };
      const res = await fetch(`${API_URL}/api/analyze-claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const newClaim = await res.json();
      toast.success("Claim analyzed", { description: `${newClaim.risk_level} risk • $${newClaim.expected_loss_usd} at risk` });
      await fetchQueue();
      setSelected(newClaim);
    } catch (e) {
      toast.error("Analysis failed");
    }
  };

  const handleAccept = (claim: Claim) => {
    toast.success(`Protected $${claim.expected_loss_usd.toLocaleString()}`, {
      description: "Agent correction accepted. Claim removed from queue."
    });
    // Subtle success animation via state (could expand with confetti lib later)
    setClaims(prev => prev.filter(c => c.claim_id !== claim.claim_id));
    setSelected(null);
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Auditor Worklist</h1>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-[var(--text-muted)]">
              Bounded knapsack queue — sorted by Expected Financial Loss (EL<sub>i</sub> = V<sub>i</sub> × P<sub>i</sub>)
            </p>
            {mode === "treasury" && (
              <span className="text-xs px-2 py-0.5 bg-[var(--accent)]/10 text-[var(--accent)] rounded-full font-medium">
                YIELD MANAGEMENT ACTIVE
              </span>
            )}
          </div>
          {mode === "treasury" && (
            <div className="mt-2 p-3 bg-[var(--accent)]/5 border border-[var(--accent)]/20 rounded-2xl text-xs text-[var(--text-muted)] max-w-2xl">
              <strong>Treasury Mode Active:</strong> We multiply denial risk by payer slowness. 
              A $40k claim from a 45-day payer can outrank a $70k claim from Medicare because the trapped cash hurts operations more. This is Dynamic Yield Management for healthcare revenue.
            </div>
          )}
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => fetchQueue(mode === "expected_loss" ? "treasury" : "expected_loss")} 
            className={`btn ${mode === "treasury" ? "btn-primary" : "btn-ghost"}`}
          >
            {mode === "expected_loss" ? "Switch to Treasury Optimization Mode" : "Switch to Traditional Risk Mode"}
          </button>
          <button onClick={() => setShowNewClaimModal(true)} className="btn btn-primary">New Claim</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Bounded Knapsack Priority Table */}
        <div className="lg:col-span-7 card p-0 overflow-hidden">
          {loading ? (
            <div className="space-y-2 p-2">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-16 bg-[var(--bg)] rounded-2xl animate-pulse" />
              ))}
            </div>
          ) : claims.length === 0 ? (
            <div className="p-8 text-center">No claims. Load demo data from Overview.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-[var(--bg)] text-[var(--text-muted)] text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left p-3">Claim</th>
                    <th className="text-right p-3">Value</th>
                    <th className="text-center p-3">P<sub>i</sub></th>
                    <th className="text-right p-3">EL<sub>i</sub></th>
                    <th className="text-center p-3">Doc</th>
                    <th className="text-center p-3">Justify</th>
                    <th className="text-center p-3">Mismatch</th>
                    <th className="text-center p-3">Codes</th>
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
                      className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--bg)] ${selected?.claim_id === claim.claim_id ? "bg-[var(--bg)]" : ""}`}
                    >
                      <td className="p-3">
                        <div className="font-mono text-xs">{claim.claim_id}</div>
                        {claim.knapsack_selected && (
                          <span className="text-[10px] text-[var(--accent)] font-medium">KNAPSACK TOP-K</span>
                        )}
                      </td>
                      <td className="p-3 text-right tabular-nums">${claim.claim_value_usd.toLocaleString()}</td>
                      <td className="p-3 text-center">
                        <span className={`risk-pill risk-${claim.risk_level} text-[10px]`}>
                          {(claim.denial_probability * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="p-3 text-right font-semibold tabular-nums">${claim.expected_loss_usd.toLocaleString()}</td>
                      <td className="p-3 text-center">{claim.documentation_complete === 0 ? "❌" : "✓"}</td>
                      <td className="p-3 text-center">{claim.clinical_justification_present === 0 ? "❌" : "✓"}</td>
                      <td className="p-3 text-center">{claim.procedure_mismatch_flag === 1 ? "⚠" : "—"}</td>
                      <td className="p-3 text-center text-xs font-mono">
                        {(claim.predicted_denial_codes || []).join(", ") || "—"}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Resolve Action Drawer */}
        <div className="lg:col-span-5 card p-6 min-h-[420px]">
          {!selected ? (
            <div className="h-full flex items-center justify-center text-center text-[var(--text-muted)]">
              Select a claim from the queue to view agent analysis, confidence, and actions.
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
                  <div className="font-mono text-xs text-[var(--text-muted)]">{selected.claim_id}</div>
                  <div className="text-xl font-semibold">${selected.claim_value_usd.toLocaleString()}</div>
                </div>
                <div className={`risk-pill risk-${selected.risk_level}`}>{selected.risk_level}</div>
              </div>

              <div className="my-6 space-y-4 text-sm">
                {selected.patient_chart_notes && (
                  <div>
                    <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">PATIENT CHART</div>
                    <div className="bg-[var(--bg)] p-4 rounded-xl border border-[var(--border)] leading-relaxed text-xs max-h-32 overflow-auto">
                      {selected.patient_chart_notes}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">AI REASONING</div>
                  <div className="text-sm">{selected.explanation || "No explanation available."}</div>
                </div>
                <div>
                  <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">AGENT CORRECTION DRAFT</div>
                  <div className="bg-[var(--bg)] p-4 rounded-xl border border-[var(--border)] leading-relaxed">
                    {selected.agent_correction_draft || "High-quality correction will appear here after full analysis."}
                  </div>
                </div>

                {selected.explanation && (
                  <div>
                    <div className="text-[var(--text-muted)] text-xs tracking-widest mb-1">EXPLANATION</div>
                    <div>{selected.explanation}</div>
                  </div>
                )}

                {selected.confidence !== undefined && (
                  <div className="text-xs">Agent Confidence: <span className="font-semibold">{(selected.confidence * 100).toFixed(0)}%</span></div>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button onClick={() => handleAccept(selected)} className="btn btn-primary flex-1">Resolve &amp; Protect</button>
                <button 
                  onClick={() => window.location.href = `/studio?claim=${selected.claim_id}`} 
                  className="btn btn-ghost flex-1"
                >
                  Open in Terminal
                </button>
                <button onClick={() => setSelected(null)} className="btn btn-ghost flex-1">Close</button>
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
          fetchQueue();
          setSelected(result);
        }}
      />
    </div>
  );
}
