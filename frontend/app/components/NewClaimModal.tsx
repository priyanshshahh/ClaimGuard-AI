"use client";

import { useState } from "react";
import { toast } from "sonner";
import { API_URL, saveClaimToHistory } from "../../lib/api";

interface NewClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: any) => void;
}

export function NewClaimModal({ isOpen, onClose, onSuccess }: NewClaimModalProps) {
  const [formData, setFormData] = useState({
    claim_id: `CLM-${Date.now().toString().slice(-6)}`,
    claim_value_usd: 45000,
    payer_id: "AETNA",
    icd_10_code: "M17.11",
    cpt_code: "27447",
    patient_chart_notes: "67 y/o female with severe right knee OA. X-ray confirmed joint space narrowing and osteophytes. Failed 8 months conservative management (PT, NSAIDs, injections). Pain 8/10, ambulation severely limited. TKA medically necessary."
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_URL}/api/analyze-claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Analysis failed");
      }

      const result = await res.json();
      saveClaimToHistory(result);
      toast.success("Claim Analyzed Successfully", {
        description: `${result.risk_level} risk • $${result.expected_loss_usd} at risk • ${(result.confidence * 100).toFixed(0)}% confidence`
      });

      onSuccess?.(result);
      onClose();
      
      // Optionally navigate to studio or queue
      setTimeout(() => {
        window.location.href = "/studio";
      }, 800);

    } catch (error: any) {
      toast.error("Analysis Failed", {
        description: error.message || "Please check backend connection"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="new-claim-title" className="bg-[var(--bg-elevated)] rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-auto border border-[var(--border)]">
        <div className="p-6 border-b border-[var(--border)] flex justify-between items-center">
          <div>
            <h3 id="new-claim-title" className="text-xl font-semibold">Analyze New Claim</h3>
            <p className="text-sm text-[var(--text-muted)]">Run full agentic + ML + policy analysis</p>
          </div>
          <button onClick={onClose} aria-label="Close dialog" className="text-2xl text-[var(--text-muted)] hover:text-[var(--text)]">×</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="nc-claim-id" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">CLAIM ID</label>
              <input
                id="nc-claim-id"
                type="text"
                name="claim_id"
                value={formData.claim_id}
                onChange={e => handleChange('claim_id', e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-2.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="nc-claim-value" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">CLAIM VALUE (USD)</label>
              <input
                id="nc-claim-value"
                type="number"
                name="claim_value_usd"
                inputMode="decimal"
                value={formData.claim_value_usd}
                onChange={e => handleChange('claim_value_usd', parseFloat(e.target.value))}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-2.5 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="nc-payer" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">PAYER</label>
              <select
                id="nc-payer"
                name="payer_id"
                value={formData.payer_id}
                onChange={e => handleChange('payer_id', e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-2.5 text-sm"
              >
                <option value="AETNA">Aetna</option>
                <option value="UHC">UnitedHealthcare</option>
                <option value="BCBS">Blue Cross Blue Shield</option>
                <option value="MEDICARE">Medicare</option>
                <option value="MEDICAID">Medicaid</option>
              </select>
            </div>
            <div>
              <label htmlFor="nc-icd" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">ICD-10 CODE</label>
              <input
                id="nc-icd"
                type="text"
                name="icd_10_code"
                value={formData.icd_10_code}
                onChange={e => handleChange('icd_10_code', e.target.value)}
                className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-2.5 text-sm"
              />
            </div>
          </div>

          <div>
            <label htmlFor="nc-cpt" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">CPT CODE</label>
            <input
              id="nc-cpt"
              type="text"
              name="cpt_code"
              value={formData.cpt_code}
              onChange={e => handleChange('cpt_code', e.target.value)}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-2.5 text-sm"
            />
          </div>

          <div>
            <label htmlFor="nc-notes" className="text-xs font-medium text-[var(--text-muted)] block mb-1.5">PHYSICIAN NOTES</label>
            <textarea
              id="nc-notes"
              name="patient_chart_notes"
              rows={5}
              value={formData.patient_chart_notes}
              onChange={e => handleChange('patient_chart_notes', e.target.value)}
              className="w-full bg-[var(--bg)] border border-[var(--border)] rounded-2xl px-4 py-3 text-sm font-mono"
            />
          </div>

          <div className="flex justify-end gap-x-3 pt-4 border-t border-[var(--border)]">
            <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
            <button 
              type="submit" 
              disabled={isSubmitting} 
              className="btn btn-primary flex items-center gap-2"
            >
              {isSubmitting ? "Running Agentic Analysis..." : "Run Full Analysis"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
