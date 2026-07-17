"use client";

import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, Legend } from 'recharts';
import { toast } from 'sonner';
import jsPDF from 'jspdf';
import { motion } from 'framer-motion';
import { API_URL } from '../../lib/api';

interface DashboardMetrics {
  total_pipeline_liquidity?: number;
  predicted_revenue_leakage?: number;
  total_revenue_at_risk?: number;
  total_claims?: number;
  high_risk_count?: number;
  denial_code_breakdown?: { code: string; count: number }[];
  payer_trends?: { payer_id: string; avg_prob: number; claim_count: number }[];
}

export default function Reports() {
  const [claims, setClaims] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics>({});
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [queueRes, metricsRes] = await Promise.all([
          fetch(`${API_URL}/api/priority-queue?mode=expected_loss`),
          fetch(`${API_URL}/api/dashboard-metrics`),
        ]);
        const queueData = await queueRes.json();
        setClaims(queueData.claims || []);
        setMetrics(await metricsRes.json());
      } catch (e) {
        setClaims([
          { claim_id: "CLM-ONC-3914", claim_value_usd: 187500, expected_loss_usd: 78750, payer_days_to_pay: 28, risk_level: "MEDIUM", cash_flow_urgency: 1240 },
          { claim_id: "CLM-SPINE-5529", claim_value_usd: 67300, expected_loss_usd: 45764, payer_days_to_pay: 42, risk_level: "HIGH", cash_flow_urgency: 1890 },
        ]);
      }
      setLoading(false);
    };
    loadData();

    const savedHistory = localStorage.getItem('claimHistory');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
  }, []);

  const treasuryData = claims.map(c => ({
    name: c.claim_id,
    "Expected Loss": c.expected_loss_usd,
    "Cash Urgency": c.cash_flow_urgency || (c.expected_loss_usd * (c.payer_days_to_pay / 20))
  }));

  const riskDistribution = [
    { name: 'HIGH', value: claims.filter(c => c.risk_level === 'HIGH').length, fill: '#dc2626' },
    { name: 'MEDIUM', value: claims.filter(c => c.risk_level === 'MEDIUM').length, fill: '#d97706' },
    { name: 'LOW', value: claims.filter(c => c.risk_level === 'LOW').length, fill: '#059669' },
  ].filter(d => d.value > 0);

  const totalAtRisk = metrics.predicted_revenue_leakage ?? claims.reduce((sum, c) => sum + (c.expected_loss_usd || 0), 0);
  const totalLiquidity = metrics.total_pipeline_liquidity ?? claims.reduce((sum, c) => sum + (c.claim_value_usd || 0), 0);
  const denialCodes = metrics.denial_code_breakdown?.length
    ? metrics.denial_code_breakdown
    : [{ code: "CO-16", count: 2 }, { code: "CO-11", count: 1 }];
  const payerTrends = (metrics.payer_trends || []).map(p => ({
    payer: p.payer_id,
    "Avg Denial Prob": Math.round((p.avg_prob || 0) * 100),
    claims: p.claim_count,
  }));

  const saveToHistory = (claim: any) => {
    const entry = {
      ...claim,
      analyzedAt: new Date().toISOString()
    };
    const updatedHistory = [entry, ...history].slice(0, 50); // Keep last 50
    setHistory(updatedHistory);
    localStorage.setItem('claimHistory', JSON.stringify(updatedHistory));
    toast.success("Claim saved to History");
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('claimHistory');
    toast.success("History cleared");
  };

  const exportCSV = () => {
    const csv = "Claim ID,Value (USD),Expected Loss (USD),Payer Days to Pay,Cash Urgency Score,Risk Level\n" +
      claims.map(c => `${c.claim_id},${c.claim_value_usd},${c.expected_loss_usd},${c.payer_days_to_pay || ''},${c.cash_flow_urgency || ''},${c.risk_level}`).join("\n");
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ClaimGuard_Executive_Report_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    
    toast.success("CSV Report exported");
  };

  const exportPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text("ClaimGuard AI - Executive Report", 20, 20);
    doc.setFontSize(11);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 20, 28);
    doc.text(`Total Claims: ${claims.length}  |  Total Revenue at Risk: $${totalAtRisk.toLocaleString()}`, 20, 36);

    let y = 50;
    claims.forEach((c, index) => {
      if (y > 260) {
        doc.addPage();
        y = 20;
      }
      doc.text(`${index + 1}. ${c.claim_id} | Value: $${c.claim_value_usd.toLocaleString()} | Risk: ${c.risk_level} | Expected Loss: $${c.expected_loss_usd}`, 20, y);
      y += 8;
    });

    doc.save(`ClaimGuard_Report_${new Date().toISOString().slice(0,10)}.pdf`);
    toast.success("PDF Report exported");
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {loading ? (
        <div className="space-y-6">
          <div className="h-8 w-64 skeleton rounded" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 skeleton rounded-3xl" />
            ))}
          </div>
          <div className="h-80 skeleton rounded-3xl" />
        </div>
      ) : (
        <>
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Executive Liquidity Dashboard</h1>
          <p className="text-[var(--text-muted)]">Pipeline liquidity • Predicted revenue leakage • Denial code trends</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowHistory(true)} className="btn btn-ghost">View Claim History</button>
          <button onClick={exportCSV} className="btn btn-primary">Export CSV</button>
          <button onClick={exportPDF} className="btn btn-ghost">Export PDF</button>
        </div>
      </div>

      {/* Executive KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
          <div className="text-xs text-[var(--text-muted)]">TOTAL PIPELINE LIQUIDITY</div>
          <div className="text-3xl font-semibold tabular-nums mt-1">${totalLiquidity.toLocaleString()}</div>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="card p-5">
          <div className="text-xs text-[var(--text-muted)]">PREDICTED REVENUE LEAKAGE</div>
          <div className="text-3xl font-semibold tabular-nums mt-1 text-red-600">${totalAtRisk.toLocaleString()}</div>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card p-5">
          <div className="text-xs text-[var(--text-muted)]">CLAIMS MONITORED</div>
          <div className="text-3xl font-semibold tabular-nums mt-1">{metrics.total_claims ?? claims.length}</div>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="card p-5">
          <div className="text-xs text-[var(--text-muted)]">HIGH-RISK CLAIMS</div>
          <div className="text-3xl font-semibold tabular-nums mt-1">{metrics.high_risk_count ?? claims.filter(c => c.risk_level === "HIGH").length}</div>
        </motion.div>
      </div>

      {/* Denial Code Breakdown + Payer Trend Lines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="font-semibold mb-4">Predicted Denial Code Breakdown</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={denialCodes}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="code" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#dc2626" radius={4} name="Claims" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-2">CO-11, CO-16, CO-50, CO-97 — standardized CARC denial categories</div>
        </div>

        <div className="card p-6">
          <div className="font-semibold mb-4">Payer Denial Probability Trends</div>
          <div className="h-64">
            {payerTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={payerTrends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="payer" />
                  <YAxis unit="%" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="Avg Denial Prob" stroke="#0a4d8c" strokeWidth={2} dot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-[var(--text-muted)] text-sm">Analyze claims to populate payer trends</div>
            )}
          </div>
        </div>
      </div>

      {/* Treasury vs Risk Chart - Core differentiator */}
      <div className="card p-6">
        <div className="font-semibold mb-4">Treasury Optimization vs Traditional Expected Loss</div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={treasuryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="Expected Loss" fill="#0a4d8c" radius={4} />
              <Bar dataKey="Cash Urgency" fill="#0d9488" radius={4} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="text-xs text-[var(--text-muted)] mt-3">Claims with slow payers (BCBS 42 days) rise dramatically in priority when cash flow is considered — this is our core competitive advantage.</div>
      </div>

      {/* Risk Distribution + Payer Speed Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="font-semibold mb-4">Denial Risk Distribution</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie 
                  data={riskDistribution} 
                  dataKey="value" 
                  nameKey="name" 
                  cx="50%" 
                  cy="50%" 
                  outerRadius={90} 
                  label={({name, percent}) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {riskDistribution.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.fill} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6">
          <div className="font-semibold mb-4">Payer Payment Speed Impact on Priority</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={claims.map(c => ({
                name: c.claim_id,
                "Payment Speed (days)": c.payer_days_to_pay || 30,
                "Cash Urgency Score": c.cash_flow_urgency || 0
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="Payment Speed (days)" fill="#0a4d8c" name="Days to Pay" />
                <Bar dataKey="Cash Urgency Score" fill="#0d9488" name="Treasury Urgency" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-3">
            Longer payment cycles from certain payers (e.g. 42+ days) dramatically increase a claim's priority in Treasury mode.
          </div>
        </div>
      </div>

      {/* Financial Optimization Explanations */}
      <div className="card p-8">
        <div className="font-semibold text-xl mb-4">Understanding Our Financial Optimization Engine</div>
        
        <div className="grid md:grid-cols-2 gap-8 text-sm">
          <div>
            <div className="font-semibold text-[var(--primary)] mb-2">Traditional Expected Loss</div>
            <p className="text-[var(--text-muted)]">
              Most platforms only look at (Claim Value × Denial Probability). This is useful but incomplete — it ignores how long the money will be tied up.
            </p>
          </div>
          <div>
            <div className="font-semibold text-[var(--accent)] mb-2">Dynamic Treasury Optimization (Our Edge)</div>
            <p className="text-[var(--text-muted)]">
              We calculate <strong>Cash Flow Urgency</strong> = (Expected Loss × Payer Slowness Factor) / √(Days to Pay).<br/><br/>
              This means a $50k claim from a slow payer (45 days) can rank higher than a $100k claim from Medicare (14 days) because the trapped cash is more damaging to operations.
            </p>
          </div>
        </div>

        <div className="mt-6 p-4 bg-[var(--bg)] rounded-2xl text-xs border border-[var(--border)]">
          <strong>How to read this:</strong> Treasury mode is a prioritization heuristic — it reorders the same claims so that slow-payer, high-liquidity-impact claims surface first. ClaimGuard runs on public CMS CERT audit data and has no production pilot, so no cash-collection outcome is claimed here; the charts above show the reordering effect on the current (synthetic/holdout) claim set only.
        </div>
      </div>

      {/* Claim History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-elevated)] rounded-3xl w-full max-w-4xl max-h-[80vh] overflow-auto border border-[var(--border)]">
            <div className="p-6 border-b flex justify-between items-center sticky top-0 bg-[var(--bg-elevated)]">
              <h3 className="text-xl font-semibold">Claim History ({history.length})</h3>
              <div className="flex gap-2">
                <button onClick={clearHistory} className="text-sm text-red-500 hover:underline">Clear All</button>
                <button onClick={() => setShowHistory(false)} className="text-xl">×</button>
              </div>
            </div>
            <div className="p-6">
              {history.length === 0 ? (
                <p className="text-[var(--text-muted)]">No claims analyzed yet. Use the Agent Studio or Queue to analyze claims.</p>
              ) : (
                <div className="space-y-3">
                  {history.map((h, i) => (
                    <div key={i} className="p-4 border border-[var(--border)] rounded-2xl">
                      <div className="flex justify-between">
                        <div>
                          <span className="font-mono">{h.claim_id}</span> — ${h.claim_value_usd?.toLocaleString()}
                        </div>
                        <div className="text-xs text-[var(--text-muted)]">{new Date(h.analyzedAt).toLocaleString()}</div>
                      </div>
                      <div className="text-sm mt-1">Risk: <strong>{h.risk_level}</strong> | Expected Loss: ${h.expected_loss_usd}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
}
