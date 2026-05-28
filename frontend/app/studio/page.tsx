"use client";

import React, { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';
import { NewClaimModal } from "../components/NewClaimModal";
import { API_URL, saveClaimToHistory } from "../../lib/api";

interface AnalysisResult {
  claim_id?: string;
  documentation_complete: number;
  clinical_justification_present?: number;
  procedure_mismatch_flag?: number;
  procedure_mismatch: number;
  agent_correction_draft: string;
  explanation: string;
  confidence: number;
  missing_elements: string[];
  risk_level?: string;
  denial_probability?: number;
  predicted_denial_codes?: string[];
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
  const [notes, setNotes] = useState("45 y/o M with type 2 diabetes follow-up. Reviewed labs. Adjusted metformin dose. Brief visit, no time documented.");
  const [icd, setIcd] = useState("E11.9");
  const [cpt, setCpt] = useState("99214");
  const [payer, setPayer] = useState("AETNA");

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [policy, setPolicy] = useState<PolicyResult | null>(null);
  const [appeal, setAppeal] = useState<AppealResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);

  // Ambient Pre-Signature Auditing - debounced real-time analysis
  const runAmbientAnalysis = useCallback(async (currentNotes: string) => {
    if (currentNotes.length < 40) return;

    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_URL}/api/analyze-claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: "AMBIENT-" + Date.now(),
          claim_value_usd: 42000,
          payer_id: payer,
          icd_10_code: icd,
          cpt_code: cpt,
          patient_chart_notes: currentNotes
        })
      });
      const data = await res.json();
      setAnalysis(data);
      saveClaimToHistory(data);
    } catch (e: any) {
      if (currentNotes.length > 120) {
        toast.error("Real-time analysis hiccup", { 
          description: "Continuing to type will retry automatically" 
        });
      }
    } finally {
      setIsAnalyzing(false);
    }
  }, [payer, icd, cpt]);

  // Debounce for ambient typing
  const debouncedAnalyze = useCallback(
    debounce((notes: string) => runAmbientAnalysis(notes), 650),
    [runAmbientAnalysis]
  );

  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setNotes(val);
    debouncedAnalyze(val);
  };

  // Manual full analysis (for when user wants to force it)
  const runFullAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_URL}/api/analyze-claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: "MANUAL-" + Date.now(),
          claim_value_usd: 42000,
          payer_id: payer,
          icd_10_code: icd,
          cpt_code: cpt,
          patient_chart_notes: notes
        })
      });
      if (!res.ok) throw new Error("Analysis failed");
      const data = await res.json();
      setAnalysis(data);
      saveClaimToHistory(data);
      toast.success("Full analysis complete", { description: `${(data.confidence * 100).toFixed(0)}% confidence` });
    } catch (e: any) {
      const message = e?.message || "Backend may be busy or unreachable";
      toast.error("Analysis failed", { description: message });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Self-Healing Data Retrieval (simulated enrichment)
  const handleSelfHealing = async () => {
    if (!analysis) return;
    setIsEnriching(true);

    // Simulate fetching missing labs/history from EHR
    await new Promise(r => setTimeout(r, 850));

    const enrichedNotes = notes + "\n\n[EHR ENRICHED] Patient weight 187 lbs, HbA1c 6.8, no recent falls, lives independently, failed 2 rounds of corticosteroid injections.";

    try {
      const res = await fetch(`${API_URL}/api/analyze-claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: "HEALED-" + Date.now(),
          claim_value_usd: 42000,
          payer_id: payer,
          icd_10_code: icd,
          cpt_code: cpt,
          patient_chart_notes: enrichedNotes
        })
      });
      const healed = await res.json();
      setAnalysis(healed);
      setNotes(enrichedNotes);
      toast.success("Self-Healing Complete", { description: "EHR data retrieved. Risk profile updated." });
    } catch (e) {
      toast.error("Enrichment failed");
    }
    setIsEnriching(false);
  };

  const runPolicyCheck = async () => {
    try {
      const res = await fetch(`${API_URL}/api/check-policy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ icd, cpt, payer, notes })
      });
      const data: PolicyResult = await res.json();
      setPolicy(data);
      toast.success(`Policy: ${data.compliance_status}`);
    } catch (e) {
      toast.error("Policy check failed");
    }
  };

  const generateAppeal = async () => {
    if (!analysis) {
      toast.error("Run analysis first");
      return;
    }
    try {
      const res = await fetch(
        `${API_URL}/api/generate-appeal?claim_id=${encodeURIComponent(analysis.claim_id || "DEMO")}&denial_reason=Documentation%20insufficient`,
        { method: "POST" }
      );
      const data: AppealResult = await res.json();
      setAppeal(data);
      toast.success("Appeal letter generated");
    } catch (e) {
      toast.error("Appeal generation failed");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-[-1.5px]">Live Agentic Evaluation Terminal</h1>
        <p className="text-[var(--text-muted)] mt-1">
          Paste a physician note, assign CPT/ICD codes, and watch P<sub>i</sub> update in real time.
          Add &quot;spent 35 minutes counseling patient&quot; for CPT 99214 to see risk drop.
        </p>
      </div>

      {/* Ambient Pre-Signature Auditing Widget */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="font-semibold flex items-center gap-2">Ambient Pre-Signature Auditor <span className="text-xs px-2 py-0.5 bg-[var(--accent)]/10 text-[var(--accent)] rounded-full">LIVE</span></div>
            <div className="text-sm text-[var(--text-muted)]">Type or paste notes — the agent analyzes in real time before the physician signs.</div>
          </div>
          <button onClick={handleSelfHealing} disabled={!analysis || isEnriching} className="btn btn-primary text-sm disabled:opacity-50">
            {isEnriching ? "Retrieving from EHR..." : "Self-Heal: Fetch Missing Data"}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <textarea
              value={notes}
              onChange={handleNotesChange}
              className="w-full h-64 p-4 font-mono text-sm bg-[var(--bg)] border border-[var(--border)] rounded-2xl resize-y focus:outline-none focus:border-[var(--primary)]"
              placeholder="Start typing clinical notes here..."
            />
            <div className="flex gap-2 mt-3 text-xs items-center">
              <input value={icd} onChange={e => setIcd(e.target.value)} className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl" />
              <input value={cpt} onChange={e => setCpt(e.target.value)} className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl" />
              <select value={payer} onChange={e => setPayer(e.target.value)} className="px-3 py-1 bg-[var(--bg)] border border-[var(--border)] rounded-xl">
                <option>AETNA</option><option>UHC</option><option>BCBS</option><option>MEDICARE</option><option>MEDICAID</option>
              </select>

              <button 
                onClick={runFullAnalysis} 
                disabled={isAnalyzing}
                className="ml-auto btn btn-primary text-xs px-4 py-1.5"
              >
                {isAnalyzing ? "Analyzing..." : "Run Agentic Analysis"}
              </button>
            </div>
          </div>

          {/* Live Agent Output */}
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
                  <div className="text-[var(--accent)] text-sm animate-pulse">Agent thinking in real time...</div>
                </motion.div>
              ) : analysis ? (
                <motion.div
                  key="analysis"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4 text-sm"
                >
                  <RiskDial probability={analysis.denial_probability ?? 0.5} riskLevel={analysis.risk_level || "MEDIUM"} />

                  <div className="flex items-center gap-2 flex-wrap">
                    <div>Confidence: <span className="font-semibold">{(analysis.confidence * 100).toFixed(0)}%</span></div>
                    {(analysis.predicted_denial_codes || []).map((code, i) => (
                      <span key={`${code}-${i}`} className="text-[10px] px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-mono">{code}</span>
                    ))}
                  </div>

                  <div>
                    <div className="uppercase text-[10px] tracking-widest text-[var(--text-muted)] mb-1">Agent Correction Draft</div>
                    <div className="text-[var(--text)] leading-relaxed bg-white dark:bg-slate-900 p-4 rounded-xl border">{analysis.agent_correction_draft}</div>
                  </div>

                  {analysis.missing_elements?.length > 0 && (
                    <div>
                      <div className="text-[var(--text-muted)] text-xs mb-1">Missing Elements (Self-Heal Recommended)</div>
                      <ul className="list-disc pl-5 text-xs space-y-0.5">
                        {analysis.missing_elements.map((m, i) => <li key={i}>{m}</li>)}
                      </ul>
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button onClick={runPolicyCheck} className="btn btn-ghost text-xs flex-1">Run Payer Policy Check</button>
                    <button onClick={generateAppeal} className="btn btn-ghost text-xs flex-1">Generate Appeal Letter</button>
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

      {/* Policy & Appeal Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {policy && (
          <div className="card p-6">
            <div className="font-semibold mb-3 text-[var(--accent)]">Payer Policy Intelligence</div>
            <div className="text-sm space-y-2">
              <div><strong>Policy:</strong> {policy.policy_reference}</div>
              <div className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${policy.compliance_status.includes('COMPLIANT') ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{policy.compliance_status}</div>
              <div>{policy.risk_summary}</div>
            </div>
          </div>
        )}

        {appeal && (
          <div className="card p-6">
            <div className="font-semibold mb-3 text-[var(--accent)]">Auto-Generated Appeal</div>
            <div className="text-sm font-medium mb-2">{appeal.subject}</div>
            <div className="text-xs bg-[var(--bg)] p-4 rounded-xl max-h-48 overflow-auto border">{appeal.body}</div>
            <div className="text-[10px] mt-2 text-[var(--text-muted)]">Recommended: {appeal.recommended_attachments.join(", ")}</div>
          </div>
        )}
      </div>
    </div>
  );
}

// Denial probability dial (P_i)
function RiskDial({ probability, riskLevel }: { probability: number; riskLevel: string }) {
  const pct = Math.round(probability * 100);
  const color = pct >= 75 ? "#dc2626" : pct >= 45 ? "#d97706" : "#059669";
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (probability * circumference);

  return (
    <div className="flex items-center gap-6">
      <div className="relative w-32 h-32">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="var(--border)" strokeWidth="10" />
          <circle
            cx="60" cy="60" r="54" fill="none"
            stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold tabular-nums">{pct}%</span>
          <span className="text-[10px] text-[var(--text-muted)]">P<sub>i</sub></span>
        </div>
      </div>
      <div>
        <div className={`risk-pill risk-${riskLevel} inline-block mb-1`}>{riskLevel}</div>
        <div className="text-xs text-[var(--text-muted)]">XGBoost denial probability</div>
      </div>
    </div>
  );
}

// Simple debounce helper
function debounce<T extends (...args: any[]) => any>(fn: T, delay: number) {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}
