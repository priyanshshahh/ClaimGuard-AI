"use client";

import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch, saveClaimToHistory } from "../../lib/api";
import { DEMO_MODE } from "../../lib/demo";

interface QueueClaimMatch {
  claim_id: string;
  claim_value_usd?: number;
  payer_id?: string;
  icd_10_code?: string;
  cpt_code?: string;
  patient_chart_notes?: string;
}

interface AnalysisResult {
  claim_id?: string;
  documentation_complete: number;
  clinical_justification_present?: number;
  procedure_mismatch_flag?: number;
  agent_correction_draft: string;
  explanation: string;
  confidence: number;
  missing_elements: string[];
  risk_level?: string;
  denial_probability?: number;
  predicted_denial_codes?: string[];
  carc_code?: string | null;
  carc_group?: string | null;
  carc_reasons?: {
    carc_code: string;
    carc_desc: string;
    rarc_code: string;
    group_code: string;
  }[];
  top_drivers?: { label: string; contribution: number; direction: string }[];
}

interface PolicyResult {
  payer: string;
  policy_reference: string;
  compliance_status: string;
  risk_summary: string;
  required_documentation: string[];
}

interface AppealResult {
  subject: string;
  body: string;
  recommended_attachments: string[];
}

export default function AgentStudio() {
  const [notes, setNotes] = useState(
    "45 y/o M with type 2 diabetes follow-up. Reviewed labs. Adjusted metformin dose. Brief visit, no time documented.",
  );
  const [icd, setIcd] = useState("E11.9");
  const [cpt, setCpt] = useState("99214");
  const [payer, setPayer] = useState("AETNA");
  // Kept as a string so the field can be empty mid-edit instead of snapping to a default.
  const [claimValue, setClaimValue] = useState("500");

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [policy, setPolicy] = useState<PolicyResult | null>(null);
  const [appeal, setAppeal] = useState<AppealResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);

  const parsedClaimValue = () => {
    const n = parseFloat(claimValue);
    return Number.isFinite(n) && n > 0 ? n : 500;
  };

  const buildPayload = (currentNotes: string, claimId: string) => ({
    claim_id: claimId,
    claim_value_usd: parsedClaimValue(),
    payer_id: payer,
    icd_10_code: icd,
    cpt_code: cpt,
    patient_chart_notes: currentNotes,
  });

  const runAmbientAnalysis = async (currentNotes: string) => {
    if (currentNotes.length < 40) return;

    setIsAnalyzing(true);
    try {
      const data = await apiFetch<AnalysisResult>("/api/analyze-claim", {
        method: "POST",
        body: JSON.stringify(buildPayload(currentNotes, "AMBIENT-" + Date.now())),
      });
      setAnalysis(data);
      saveClaimToHistory(data as unknown as Record<string, unknown>);
    } catch {
      if (currentNotes.length > 120) {
        toast.error("Real-time analysis hiccup", {
          description: "Continuing to type will retry automatically",
        });
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Debounce ambient analysis via a timer ref. Refs are only touched inside the
  // event handler (never during render), and setTimeout captures the latest
  // runAmbientAnalysis closure, so payer/code/value edits stay current.
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setNotes(val);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => void runAmbientAnalysis(val), 650);
  };

  // Prefill from the Queue when opened via "Open in Terminal" (/studio?claim=ID).
  useEffect(() => {
    const claimId = new URLSearchParams(window.location.search).get("claim");
    if (!claimId) return;

    let cancelled = false;
    (async () => {
      try {
        const data = await apiFetch<{ claims?: QueueClaimMatch[] }>(
          "/api/priority-queue?mode=expected_loss",
        );
        const match = (data.claims || []).find((c) => c.claim_id === claimId);
        if (!match || cancelled) return;

        if (match.patient_chart_notes) setNotes(match.patient_chart_notes);
        if (match.icd_10_code) setIcd(match.icd_10_code);
        if (match.cpt_code) setCpt(match.cpt_code);
        if (match.payer_id) setPayer(match.payer_id);
        if (typeof match.claim_value_usd === "number") {
          setClaimValue(String(match.claim_value_usd));
        }
        toast.success(`Loaded ${claimId} from the queue`);
      } catch {
        toast.error("Could not load the claim from the queue");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const runFullAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const data = await apiFetch<AnalysisResult>("/api/analyze-claim", {
        method: "POST",
        body: JSON.stringify(
          buildPayload(notes, "MANUAL-" + Date.now()),
        ),
      });
      setAnalysis(data);
      saveClaimToHistory(data as unknown as Record<string, unknown>);
      toast.success("Full analysis complete", {
        description: `${(data.confidence * 100).toFixed(0)}% confidence`,
      });
    } catch (e: unknown) {
      const message =
        e instanceof Error ? e.message : "Backend may be busy or unreachable";
      toast.error("Analysis failed", { description: message });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSelfHealing = async () => {
    if (!analysis) return;
    setIsEnriching(true);

    await new Promise((r) => setTimeout(r, 850));

    const enrichedNotes =
      notes +
      "\n\n[SIMULATED EHR ENRICHMENT — demo data, not from a real EHR] Patient weight 187 lbs, HbA1c 6.8, no recent falls, lives independently, failed 2 rounds of corticosteroid injections.";

    try {
      const healed = await apiFetch<AnalysisResult>("/api/analyze-claim", {
        method: "POST",
        body: JSON.stringify(
          buildPayload(enrichedNotes, "HEALED-" + Date.now()),
        ),
      });
      setAnalysis(healed);
      setNotes(enrichedNotes);
      toast.success("Simulated Enrichment Complete", {
        description:
          "Demo only — appended synthetic EHR fields and re-scored. No live EHR connection.",
      });
    } catch {
      toast.error("Enrichment failed");
    }
    setIsEnriching(false);
  };

  const runPolicyCheck = async () => {
    try {
      const data = await apiFetch<PolicyResult>("/api/check-policy", {
        method: "POST",
        body: JSON.stringify({ icd, cpt, payer, notes }),
      });
      setPolicy(data);
      toast.success(`Policy: ${data.compliance_status}`);
    } catch {
      toast.error("Policy check failed");
    }
  };

  const generateAppeal = async () => {
    if (!analysis) {
      toast.error("Run analysis first");
      return;
    }
    try {
      const denialReason = analysis.carc_code
        ? `CARC ${analysis.carc_code} (${analysis.carc_reasons?.[0]?.carc_desc || "denial reason"})`
        : "Documentation insufficient";
      const data = await apiFetch<AppealResult>(
        `/api/generate-appeal?claim_id=${encodeURIComponent(analysis.claim_id || "DEMO")}&denial_reason=${encodeURIComponent(denialReason)}`,
        { method: "POST" },
      );
      setAppeal(data);
      toast.success("Appeal letter generated");
    } catch {
      toast.error("Appeal generation failed");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-[-1.5px]">
          Live Agentic Evaluation Terminal
        </h1>
        <p className="text-[var(--text-muted)] mt-1">
          Paste a physician note, assign CPT/ICD codes, and watch P<sub>i</sub>{" "}
          update in real time. Add &quot;spent 35 minutes counseling patient&quot;
          for CPT 99214 to see risk drop.
        </p>
      </div>

      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="font-semibold flex items-center gap-2">
              Ambient Pre-Signature Auditor{" "}
              <span className="text-xs px-2 py-0.5 bg-[var(--accent)]/10 text-[var(--accent)] rounded-full">
                Debounced
              </span>
            </div>
            <div className="text-sm text-[var(--text-muted)]">
              Type or paste notes — analysis runs ~650ms after you stop typing.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <textarea
              aria-label="Clinical notes"
              value={notes}
              onChange={handleNotesChange}
              className="w-full h-64 p-4 font-mono text-sm bg-[var(--bg)] border border-[var(--border)] rounded-2xl resize-y focus-visible:border-[var(--primary)]"
              placeholder="Start typing clinical notes here…"
            />
            <div className="flex gap-2 mt-3 text-xs items-center flex-wrap">
              <input
                aria-label="ICD-10 code"
                value={icd}
                onChange={(e) => setIcd(e.target.value)}
                className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl"
              />
              <input
                aria-label="CPT code"
                value={cpt}
                onChange={(e) => setCpt(e.target.value)}
                className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl"
              />
              <select
                aria-label="Payer"
                value={payer}
                onChange={(e) => setPayer(e.target.value)}
                className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl"
              >
                <option>AETNA</option>
                <option>UHC</option>
                <option>BCBS</option>
                <option>MEDICARE</option>
                <option>MEDICAID</option>
              </select>
              <input
                aria-label="Claim value USD"
                type="number"
                min={1}
                inputMode="decimal"
                value={claimValue}
                onChange={(e) => setClaimValue(e.target.value)}
                onBlur={() => {
                  const n = parseFloat(claimValue);
                  if (!Number.isFinite(n) || n <= 0) setClaimValue("500");
                }}
                className="px-3 py-1 w-24 bg-[var(--bg)] border border-[var(--border)] rounded-xl"
              />

              <button
                type="button"
                onClick={() => void runFullAnalysis()}
                disabled={isAnalyzing}
                className="ml-auto btn btn-primary text-xs px-4 py-1.5"
              >
                {isAnalyzing ? "Analyzing..." : "Run Agentic Analysis"}
              </button>
            </div>
          </div>

          <div className="bg-[var(--bg)] border border-[var(--border)] rounded-2xl p-5 min-h-[260px]">
            <AnimatePresence mode="wait">
              {isAnalyzing ? (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-3"
                >
                  <div className="h-4 w-3/4 skeleton rounded" />
                  <div className="h-4 w-1/2 skeleton rounded" />
                  <div className="h-20 skeleton rounded-xl" />
                  <div className="text-[var(--accent)] text-sm animate-pulse">
                    Agent thinking in real time...
                  </div>
                </motion.div>
              ) : analysis ? (
                <motion.div
                  key="analysis"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4 text-sm"
                >
                  <RiskDial
                    probability={analysis.denial_probability ?? 0.5}
                    riskLevel={analysis.risk_level || "MEDIUM"}
                  />

                  <div className="flex items-center gap-2 flex-wrap">
                    <div>
                      Confidence:{" "}
                      <span className="font-semibold">
                        {(analysis.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    {(analysis.predicted_denial_codes || []).map((code, i) => (
                      <span
                        key={`${code}-${i}`}
                        className="text-[10px] px-2 py-0.5 bg-[var(--danger)]/10 text-[var(--danger)] rounded-full font-mono"
                      >
                        {code}
                      </span>
                    ))}
                  </div>

                  {analysis.carc_reasons && analysis.carc_reasons.length > 0 ? (
                    <div>
                      <div className="uppercase text-[10px] tracking-widest text-[var(--text-muted)] mb-1">
                        Derived Denial Reason (CARC/RARC)
                      </div>
                      <div className="space-y-1">
                        {analysis.carc_reasons.map((r, i) => (
                          <div key={i} className="text-xs">
                            <span className="font-mono">
                              CARC {r.carc_code} · {r.group_code}
                            </span>{" "}
                            — {r.carc_desc}
                          </div>
                        ))}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] mt-1">
                        Derived mapping — not a payer&apos;s actual remittance code.
                      </div>
                    </div>
                  ) : null}

                  {analysis.top_drivers && analysis.top_drivers.length > 0 ? (
                    <div>
                      <div className="uppercase text-[10px] tracking-widest text-[var(--text-muted)] mb-1">
                        Top Risk Drivers (Model)
                      </div>
                      <ul className="space-y-0.5 text-xs">
                        {analysis.top_drivers.map((d, i) => (
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

                  <div>
                    <div className="uppercase text-[10px] tracking-widest text-[var(--text-muted)] mb-1">
                      Agent Correction Draft
                    </div>
                    <div className="text-[var(--text)] leading-relaxed bg-[var(--bg-elevated)] p-4 rounded-xl border border-[var(--border)]">
                      {analysis.agent_correction_draft}
                    </div>
                  </div>

                  {analysis.missing_elements?.length > 0 ? (
                    <div>
                      <div className="text-[var(--text-muted)] text-xs mb-1">
                        Missing Elements (Self-Heal Recommended)
                      </div>
                      <ul className="list-disc pl-5 text-xs space-y-0.5">
                        {analysis.missing_elements.map((m, i) => (
                          <li key={i}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="flex gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => void runPolicyCheck()}
                      className="btn btn-ghost text-xs flex-1"
                    >
                      Run Payer Policy Check
                    </button>
                    <button
                      type="button"
                      onClick={() => void generateAppeal()}
                      className="btn btn-ghost text-xs flex-1"
                    >
                      Generate Appeal Letter
                    </button>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex items-center justify-center text-[var(--text-muted)] text-sm min-h-[220px]"
                >
                  Start typing notes above for real-time agent analysis
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {DEMO_MODE ? (
        <div className="card p-6 space-y-4">
          <div>
            <div className="font-semibold">Demo lab</div>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              Simulation tools — no live EHR connection. Enabled via{" "}
              <code className="font-mono text-xs">NEXT_PUBLIC_DEMO_MODE</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleSelfHealing()}
            disabled={!analysis || isEnriching}
            title="Demo only: appends synthetic EHR fields and re-scored. No live EHR connection."
            className="btn btn-primary text-sm disabled:opacity-50"
          >
            {isEnriching
              ? "Simulating EHR fetch..."
              : "Self-Heal: Simulate EHR Enrichment"}
          </button>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {policy ? (
          <div className="card p-6">
            <div className="font-semibold mb-3 text-[var(--accent)]">
              Payer Policy Intelligence
            </div>
            <div className="text-sm space-y-2">
              <div>
                <strong>Policy:</strong> {policy.policy_reference}
              </div>
              <div
                className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                  policy.compliance_status.includes("COMPLIANT")
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {policy.compliance_status}
              </div>
              <div>{policy.risk_summary}</div>
            </div>
          </div>
        ) : null}

        {appeal ? (
          <div className="card p-6">
            <div className="font-semibold mb-3 text-[var(--accent)]">
              Auto-Generated Appeal
            </div>
            <div
              role="alert"
              className="mb-3 p-2.5 rounded-xl text-xs font-medium bg-amber-100 text-amber-800 border border-amber-300"
            >
              ⚠ Draft — clinical review required. AI-generated; a clinician/coder
              must verify every quoted passage before submission.
            </div>
            <div className="text-sm font-medium mb-2">{appeal.subject}</div>
            <div className="text-xs bg-[var(--bg)] p-4 rounded-xl max-h-48 overflow-auto border whitespace-pre-wrap">
              {appeal.body}
            </div>
            <div className="text-[10px] mt-2 text-[var(--text-muted)]">
              Recommended: {appeal.recommended_attachments.join(", ")}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function RiskDial({
  probability,
  riskLevel,
}: {
  probability: number;
  riskLevel: string;
}) {
  const pct = Math.round(probability * 100);
  const color = pct >= 75 ? "#dc2626" : pct >= 45 ? "#d97706" : "#059669";
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - probability * circumference;

  return (
    <div className="flex items-center gap-6">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="var(--border)"
            strokeWidth="10"
          />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold tabular-nums">{pct}%</span>
          <span className="text-[10px] text-[var(--text-muted)]">
            P<sub>i</sub>
          </span>
        </div>
      </div>
      <div>
        <div className={`risk-pill risk-${riskLevel} inline-block mb-1`}>
          {riskLevel}
        </div>
        <div className="text-xs text-[var(--text-muted)]">
          XGBoost denial probability
        </div>
      </div>
    </div>
  );
}

