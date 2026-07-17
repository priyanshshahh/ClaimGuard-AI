"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { API_URL } from "../../lib/api";

interface Reliability { mean_predicted: number; fraction_positive: number }
interface Result {
  model: string; roc_auc: number; pr_auc: number; brier: number;
  log_loss: number; base_rate: number; n: number; reliability: Reliability[];
}
interface Metrics {
  config?: {
    dataset?: string; train_years?: number[]; val_year?: number; test_year?: number;
    n_train?: number; n_val?: number; n_test?: number; features?: string[];
    seed?: number; label?: string;
  };
  trained_at_utc?: string; python?: string; best_iteration?: number;
  results?: { val?: Result[]; test?: Result[] };
}

const SERVED = "xgboost_isotonic";
const fmt = (n?: number) => (n ?? 0).toLocaleString();

export default function ModelCard() {
  const [m, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/model-info`)
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then(setMetrics)
      .catch(() => setError("Could not reach the backend on :8000 to load metrics.json."));
  }, []);

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">Model Card</h1>
        <div role="alert" className="p-4 rounded-2xl border border-[var(--danger,#dc2626)]/40 bg-[var(--danger,#dc2626)]/10 text-sm">
          <strong>Backend unavailable.</strong> {error}
        </div>
      </div>
    );
  }
  if (!m) return <div className="max-w-3xl mx-auto text-[var(--text-muted)]">Loading model card…</div>;

  const cfg = m.config ?? {};
  const test = m.results?.test ?? [];
  const val = m.results?.val ?? [];
  const served = test.find((r) => r.model === SERVED);
  const servedVal = val.find((r) => r.model === SERVED);

  // Calibration-over-time: served model, validation year vs test year.
  const calib = (served?.reliability ?? []).map((pt, i) => ({
    predicted: +(pt.mean_predicted * 100).toFixed(1),
    [`Test ${cfg.test_year}`]: +(pt.fraction_positive * 100).toFixed(1),
    [`Val ${cfg.val_year}`]: servedVal?.reliability[i]
      ? +(servedVal.reliability[i].fraction_positive * 100).toFixed(1)
      : null,
  }));

  const testYearKey = `Test ${cfg.test_year}`;
  const valYearKey = `Val ${cfg.val_year}`;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Model Card</h1>
        <p className="text-[var(--text-muted)] mt-1">
          Denial-risk classifier — every number below is read live from the committed
          training run (<code className="font-mono">backend/models/metrics.json</code>). No marketing figures.
        </p>
      </div>

      {/* Provenance */}
      <section className="card p-6">
        <h2 className="font-semibold text-lg mb-4">Provenance & setup</h2>
        <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div><dt className="text-[var(--text-muted)]">Dataset</dt><dd>{cfg.dataset}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Label</dt><dd>{cfg.label}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Temporal split</dt>
            <dd>train {cfg.train_years?.join(", ")} (n={fmt(cfg.n_train)}) · val {cfg.val_year} (n={fmt(cfg.n_val)}) · test {cfg.test_year} (n={fmt(cfg.n_test)})</dd></div>
          <div><dt className="text-[var(--text-muted)]">Calibration</dt><dd>Isotonic regression fit on the {cfg.val_year} validation predictions</dd></div>
          <div><dt className="text-[var(--text-muted)]">Features ({cfg.features?.length})</dt><dd className="font-mono text-xs">{cfg.features?.join(", ")}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Reproducibility</dt><dd>seed {cfg.seed}, best iteration {m.best_iteration}, Python {m.python}</dd></div>
          <div><dt className="text-[var(--text-muted)]">Trained at</dt><dd>{m.trained_at_utc}</dd></div>
        </dl>
      </section>

      {/* Metrics */}
      <section className="card p-6">
        <h2 className="font-semibold text-lg mb-1">Held-out performance</h2>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Test year {cfg.test_year} (n={fmt(served?.n)}, base rate {((served?.base_rate ?? 0) * 100).toFixed(1)}%).
          The served model is XGBoost + isotonic calibration.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-[var(--text-muted)] text-xs uppercase tracking-wider border-b border-[var(--border)]">
              <tr>
                <th className="text-left p-2">Model</th>
                <th className="text-right p-2">ROC-AUC</th>
                <th className="text-right p-2">PR-AUC</th>
                <th className="text-right p-2">Brier</th>
                <th className="text-right p-2">Log loss</th>
              </tr>
            </thead>
            <tbody>
              {test.map((r) => (
                <tr key={r.model} className={`border-b border-[var(--border)] ${r.model === SERVED ? "font-semibold" : ""}`}>
                  <td className="p-2">{r.model}{r.model === SERVED && " (served)"}</td>
                  <td className="p-2 text-right tabular-nums">{r.roc_auc.toFixed(4)}</td>
                  <td className="p-2 text-right tabular-nums">{r.pr_auc.toFixed(4)}</td>
                  <td className="p-2 text-right tabular-nums">{r.brier.toFixed(4)}</td>
                  <td className="p-2 text-right tabular-nums">{r.log_loss.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Calibration-over-time */}
      <section className="card p-6">
        <h2 className="font-semibold text-lg mb-1">Calibration over time (served model)</h2>
        <p className="text-sm text-[var(--text-muted)] mb-4">
          Reliability curve — mean predicted vs. observed rate per decile. Points near the
          diagonal are well-calibrated. Comparing the {cfg.val_year} validation year to the
          {" "}{cfg.test_year} test year is a first, honest drift check on already-committed splits.
        </p>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={calib} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="predicted" type="number" domain={[0, "dataMax"]} unit="%"
                label={{ value: "Mean predicted", position: "insideBottom", offset: -12 }} />
              <YAxis unit="%" label={{ value: "Observed", angle: -90, position: "insideLeft" }} />
              <Tooltip />
              <Legend />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 45, y: 45 }]} stroke="var(--text-muted)" strokeDasharray="4 4" ifOverflow="extendDomain" />
              <Line type="monotone" dataKey={testYearKey} stroke="#0a4d8c" strokeWidth={2} dot={{ r: 3 }} connectNulls />
              <Line type="monotone" dataKey={valYearKey} stroke="#0d9488" strokeWidth={2} dot={{ r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-3">
          Brier score {cfg.test_year}: {served?.brier.toFixed(4)} · {cfg.val_year}: {servedVal?.brier.toFixed(4)}
          {" "}(lower is better-calibrated). A full PSI / score-distribution drift dashboard is the documented next step.
        </p>
      </section>

      {/* Intended use + limitations (honest static text) */}
      <section className="card p-6 space-y-4 text-sm">
        <div>
          <h2 className="font-semibold text-lg mb-2">Intended use</h2>
          <p className="text-[var(--text-muted)]">
            Pre-submission triage aid: rank professional claims by estimated improper-payment /
            denial risk so a human reviewer works the riskiest first. Decision support only —
            not an automated adjudication or a substitute for clinician/coder judgment.
          </p>
        </div>
        <div>
          <h2 className="font-semibold text-lg mb-2">Known limitations</h2>
          <ul className="list-disc pl-5 space-y-1 text-[var(--text-muted)]">
            <li>Trained on public CMS CERT audit data (improper-payment findings), a documented
              <em> proxy</em> for payer denials — not actual 835/EDI denial outcomes.</li>
            <li>Modest discrimination (ROC-AUC ≈ 0.745); useful for ranking, not for autonomous decisions.</li>
            <li>The agent documentation uplift and the CARC/RARC mapping are business rules /
              a derived crosswalk, not learned model outputs, and are reported separately.</li>
            <li>The overturn-rate used for expected-recovery dollars is a documented assumption, not a measured ClaimGuard result.</li>
            <li>No production claim volume, payer contracts, or closed-loop outcome feed exist for this project.</li>
          </ul>
        </div>
      </section>
    </div>
  );
}
