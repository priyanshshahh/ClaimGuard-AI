"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "../../lib/api";
import { DEMO_MODE } from "../../lib/demo";
import { PageHeader } from "../components/ui";

type ScoreMode = "base" | "uplifted";

const THRESHOLD_KEY = "cg_threshold";
const DEMO_MODE_KEY = "cg_demo_mode";
const SCORE_MODE_KEY = "cg_score_mode";

function readThreshold(): number {
  if (typeof window === "undefined") return 0.65;
  const raw = localStorage.getItem(THRESHOLD_KEY);
  const parsed = raw ? parseFloat(raw) : 0.65;
  return Number.isFinite(parsed) ? parsed : 0.65;
}

function readDemoMode(): boolean {
  if (typeof window === "undefined") return true;
  const raw = localStorage.getItem(DEMO_MODE_KEY);
  if (raw === null) return true;
  return raw === "true" || raw === "1";
}

function readScoreMode(): ScoreMode {
  if (typeof window === "undefined") return "uplifted";
  const raw = localStorage.getItem(SCORE_MODE_KEY);
  return raw === "base" ? "base" : "uplifted";
}

export default function Settings() {
  const [threshold, setThreshold] = useState(0.65);
  const [demoMode, setDemoMode] = useState(true);
  const [scoreMode, setScoreMode] = useState<ScoreMode>("uplifted");
  const [demoBusy, setDemoBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setThreshold(readThreshold());
      setDemoMode(readDemoMode());
      setScoreMode(readScoreMode());
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const saveSettings = () => {
    localStorage.setItem(THRESHOLD_KEY, String(threshold));
    localStorage.setItem(DEMO_MODE_KEY, demoMode ? "true" : "false");
    localStorage.setItem(SCORE_MODE_KEY, scoreMode);
    toast.success("Settings saved", {
      description: `Saved ${THRESHOLD_KEY}, ${DEMO_MODE_KEY}, ${SCORE_MODE_KEY} — this browser only, not synced to the backend`,
    });
  };

  const seedDemo = async () => {
    setDemoBusy(true);
    try {
      const data = await apiFetch<{ seeded: number }>("/api/seed-demo", {
        method: "POST",
      });
      toast.success(`Demo seeded: ${data.seeded} claims`);
    } catch {
      toast.error("Could not seed demo — is the API running?");
    }
    setDemoBusy(false);
  };

  const clearQueue = async () => {
    setDemoBusy(true);
    try {
      await apiFetch("/api/clear-queue", { method: "POST" });
      toast.success("Queue cleared");
    } catch {
      toast.error("Could not clear queue");
    }
    setDemoBusy(false);
  };

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader
        title="Settings"
        description="Configure how ClaimGuard protects your revenue cycle"
      />

      <div className="card p-8 space-y-8">
        <div>
          <label
            htmlFor="confidence-threshold"
            className="block text-sm font-medium mb-2"
          >
            Minimum Agent Confidence for Auto-Accept
          </label>
          <input
            id="confidence-threshold"
            type="range"
            min="0.5"
            max="0.95"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            aria-valuetext={`${(threshold * 100).toFixed(0)}%`}
            className="w-full accent-[var(--primary)]"
          />
          <div className="text-right text-sm font-mono mt-1">
            {(threshold * 100).toFixed(0)}%
          </div>
          <p className="text-xs text-[var(--text-muted)] mt-2">
            Client-side preference only — the API does not enforce this threshold yet.
          </p>
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border)] pt-6">
          <div>
            <div className="font-medium">Demo Mode (UI preference only)</div>
            <div className="text-sm text-[var(--text-muted)]">
              Remembers whether you prefer demo-oriented copy in this browser. This
              does not enable demo tools — those are gated by the{" "}
              <code className="font-mono text-xs">NEXT_PUBLIC_DEMO_MODE</code> build flag.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDemoMode(!demoMode)}
            aria-pressed={demoMode}
            aria-label="Toggle demo mode preference"
            className={`px-4 py-1.5 rounded-2xl text-sm font-medium transition ${
              demoMode
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--bg)] border"
            }`}
          >
            {demoMode ? "Enabled" : "Disabled"}
          </button>
        </div>

        <div className="border-t border-[var(--border)] pt-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="font-medium">Denial Probability Score Mode</div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] font-medium tracking-wide">
              LIVE — CHANGES THE QUEUE
            </span>
          </div>
          <p className="text-sm text-[var(--text-muted)] mb-4">
            This is a real setting: it is sent to the backend as{" "}
            <code className="font-mono text-xs">score_mode</code> and changes how the
            queue ranks claims — either the calibrated model output (
            <code className="font-mono text-xs">base</code>) or the documented
            agent-heuristic uplift (<code className="font-mono text-xs">uplifted</code>).
          </p>
          <div className="flex gap-2">
            {(["base", "uplifted"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setScoreMode(mode)}
                aria-pressed={scoreMode === mode}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                  scoreMode === mode
                    ? "bg-[var(--primary)] text-white"
                    : "bg-[var(--bg)] border border-[var(--border)]"
                }`}
              >
                {mode === "base" ? "Model base only" : "Base + uplift"}
              </button>
            ))}
          </div>
        </div>

        <div className="border-t border-[var(--border)] pt-6">
          <div className="font-medium mb-2">EHR Integration</div>
          <div className="text-sm bg-[var(--bg)] p-4 rounded-2xl border text-[var(--text-muted)]">
            Not configured. FHIR R4 ingestion is not connected in this deployment.
          </div>
        </div>
      </div>

      {DEMO_MODE ? (
        <div className="card p-8 space-y-4">
          <div>
            <div className="font-medium">Demo tools</div>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              Available because <code className="font-mono text-xs">NEXT_PUBLIC_DEMO_MODE</code> is
              enabled. Synthetic claims are labeled <code className="font-mono text-xs">is_demo=true</code>.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={seedDemo}
              disabled={demoBusy}
              className="btn btn-primary"
            >
              {demoBusy ? "Working…" : "Seed demo claims"}
            </button>
            <button
              type="button"
              onClick={clearQueue}
              disabled={demoBusy}
              className="btn btn-ghost"
            >
              Clear queue
            </button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={saveSettings}
        className="btn btn-primary w-full py-3 text-base"
      >
        Save Configuration
      </button>
    </div>
  );
}
