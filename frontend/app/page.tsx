"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiFetch } from "../lib/api";
import { DEMO_MODE } from "../lib/demo";

const PRODUCT_NAV = [
  { href: "/dashboard", label: "Workspace" },
  { href: "/queue", label: "Queue" },
  { href: "/studio", label: "Studio" },
  { href: "/model-card", label: "Model Card" },
];

type ModelInfo = {
  results?: {
    test?: Array<{ model: string; roc_auc: number }>;
  };
};

/** Restored marketing landing — route `/` only. */
export default function LandingPage() {
  const router = useRouter();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [rocAuc, setRocAuc] = useState("0.744");
  const onboardingCloseRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const hasSeenTour = localStorage.getItem("hasSeenOnboarding");
    if (!hasSeenTour) {
      const timer = setTimeout(() => setShowOnboarding(true), 1800);
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    apiFetch<ModelInfo>("/api/model-info")
      .then((m) => {
        const served = m.results?.test?.find((r) => r.model === "xgboost_isotonic");
        if (served?.roc_auc != null) setRocAuc(served.roc_auc.toFixed(3));
      })
      .catch(() => {});
  }, []);

  const launchDemo = async () => {
    try {
      const data = await apiFetch<{ seeded: number; total_revenue_at_risk: number }>(
        "/api/seed-demo",
        { method: "POST" },
      );
      toast.success(`Demo Ready: ${data.seeded} Claims Loaded`, {
        description: `$${Math.round(data.total_revenue_at_risk / 1000)}k revenue at risk — Treasury optimization active`,
      });
      setTimeout(() => {
        router.push("/dashboard");
      }, 900);
    } catch {
      toast.error("Could not connect to backend", {
        description: "Please run the backend: cd backend && uvicorn main:app --reload",
      });
    }
  };

  const goToStudio = () => {
    router.push("/studio");
  };

  const closeOnboarding = () => {
    localStorage.setItem("hasSeenOnboarding", "true");
    setShowOnboarding(false);
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "true") {
      void launchDemo();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!showOnboarding) return;
    onboardingCloseRef.current?.focus();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeOnboarding();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [showOnboarding]);

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <nav className="border-b border-[var(--border)] bg-[var(--bg-elevated)]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-2xl bg-[var(--primary)] flex items-center justify-center">
              <span className="text-white font-bold text-lg">CG</span>
            </div>
            <span className="font-semibold text-2xl tracking-tight">ClaimGuard</span>
            <span className="text-[var(--accent)] font-medium">AI</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <a
              href="#features"
              className="hidden lg:inline text-[var(--text-muted)] hover:text-[var(--text)]"
            >
              Features
            </a>
            <a
              href="#how"
              className="hidden lg:inline text-[var(--text-muted)] hover:text-[var(--text)]"
            >
              How it Works
            </a>
            <a
              href="#position"
              className="hidden lg:inline text-[var(--text-muted)] hover:text-[var(--text)]"
            >
              Positioning
            </a>
            <span className="hidden md:inline-block h-4 w-px bg-[var(--border)]" aria-hidden />
            {PRODUCT_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="hidden md:inline text-[var(--text-muted)] hover:text-[var(--text)]"
              >
                {item.label}
              </Link>
            ))}
            <Link href="/login" className="text-[var(--text-muted)] hover:text-[var(--text)]">
              Sign in
            </Link>
            <button type="button" onClick={launchDemo} className="btn btn-primary px-5 py-2 text-sm">
              Launch Live Demo
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-block px-4 py-1.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] text-sm font-medium tracking-widest mb-6">
          PRE-SUBMISSION REVENUE PROTECTION
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-7xl font-semibold tracking-tight sm:tracking-[-2px] md:tracking-[-4.5px] leading-[1.05] md:leading-[0.95] mb-6">
          Protect every dollar
          <br />
          before the claim is sent.
        </h1>

        <p className="max-w-2xl mx-auto text-lg sm:text-xl md:text-2xl text-[var(--text-muted)]">
          Score which claims need review before they hit Athena-style scrubbing or
          the clearinghouse — calibrated CERT risk, note agent, expected-loss queue.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={launchDemo}
            className="btn btn-primary w-full sm:w-auto px-8 md:px-10 py-4 text-lg md:text-xl font-semibold"
          >
            Launch Live Demo
          </button>
          <button
            type="button"
            onClick={goToStudio}
            className="btn btn-ghost w-full sm:w-auto px-6 md:px-8 py-4 text-lg md:text-xl"
          >
            Explore the Agent
          </button>
        </div>

        <div className="mt-6 flex items-center justify-center gap-4 text-sm">
          <button
            type="button"
            onClick={() => router.push("/reports")}
            className="text-[var(--text-muted)] hover:text-[var(--text)] underline"
          >
            View Reports & History
          </button>
          <span className="text-[var(--text-muted)]">·</span>
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem("hasSeenOnboarding");
              setShowOnboarding(true);
            }}
            className="text-[var(--text-muted)] hover:text-[var(--text)] underline"
          >
            Replay Welcome Tour
          </button>
        </div>

        <p className="mt-4 text-xs text-[var(--text-muted)]">
          {DEMO_MODE
            ? "Demo mode on · Full backend connected · Open dashboard without account"
            : "Sign in for your workspace · Model card for offline eval metrics"}
        </p>
      </div>

      {showOnboarding && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[100] p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="onboarding-title"
            className="bg-[var(--bg-elevated)] rounded-3xl max-w-lg w-full p-8 border border-[var(--border)]"
          >
            <h2 id="onboarding-title" className="text-2xl font-semibold mb-2">
              Welcome to ClaimGuard AI
            </h2>
            <p className="text-[var(--text-muted)] mb-6">
              Here&apos;s how to get the most out of your demo in the next 60 seconds:
            </p>

            <ol className="space-y-4 text-sm mb-8">
              <li className="flex gap-3">
                <span className="font-mono text-[var(--accent)]">01</span> Click{" "}
                <strong>Launch Live Demo</strong> to seed claims.
              </li>
              <li className="flex gap-3">
                <span className="font-mono text-[var(--accent)]">02</span> Open{" "}
                <strong>Claims Queue</strong> and toggle <strong>Treasury Mode</strong>.
              </li>
              <li className="flex gap-3">
                <span className="font-mono text-[var(--accent)]">03</span> Open{" "}
                <strong>Agent Studio</strong> for ambient auditing and appeals.
              </li>
              <li className="flex gap-3">
                <span className="font-mono text-[var(--accent)]">04</span> Visit{" "}
                <strong>Reports</strong> to export PDF/CSV executive reports.
              </li>
            </ol>

            <div className="flex gap-3">
              <button
                ref={onboardingCloseRef}
                type="button"
                onClick={closeOnboarding}
                className="btn btn-ghost flex-1"
              >
                Skip Tour
              </button>
              <button
                type="button"
                onClick={closeOnboarding}
                className="btn btn-primary flex-1"
              >
                Got it — Start Exploring
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto px-6 pb-16 -mt-8">
        <div className="text-center mb-8">
          <div className="text-sm text-[var(--accent)] font-medium tracking-widest">
            DYNAMIC TREASURY OPTIMIZATION
          </div>
          <h3 className="text-2xl font-semibold mt-2">We optimize for cash, not just risk</h3>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="card p-6 text-center">
            <div className="text-4xl font-semibold text-[var(--primary)]">14 days</div>
            <div className="mt-1 font-medium">Medicare / Fast Payers</div>
            <div className="text-xs text-[var(--text-muted)] mt-2">Lower cash-flow urgency</div>
          </div>
          <div className="card p-6 text-center">
            <div className="text-4xl font-semibold text-[var(--accent)]">42+ days</div>
            <div className="mt-1 font-medium">Slow Commercial Payers</div>
            <div className="text-xs text-[var(--text-muted)] mt-2">These claims jump in priority</div>
          </div>
          <div className="card p-6 text-center">
            <div className="text-4xl font-semibold text-[var(--primary)]">{rocAuc}</div>
            <div className="mt-1 font-medium">Denial Model ROC-AUC</div>
            <div className="text-xs text-[var(--text-muted)] mt-2">
              CMS CERT 2025 holdout — real offline eval, not a pilot
            </div>
          </div>
        </div>

        <div className="text-center mt-8">
          <button
            type="button"
            onClick={() => router.push("/reports")}
            className="btn btn-ghost text-sm"
          >
            View full Treasury vs Risk analytics in Reports →
          </button>
        </div>
      </div>

      <div className="border-y border-[var(--border)] bg-[var(--bg-elevated)] py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-center gap-x-4 text-sm text-[var(--text-muted)] text-center">
          <div>
            Built for provider-side revenue-cycle teams — trained on public CMS CERT data,
            with honest model-card metrics.
          </div>
        </div>
      </div>

      <div id="features" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <div className="text-[var(--accent)] text-sm tracking-[2px] font-medium">
            WHY CLAIMGUARD IS DIFFERENT
          </div>
          <h2 className="text-4xl font-semibold tracking-tight mt-3">
            Three layers that existing scrubbers miss
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              title: "Ambient Pre-Signature Auditing",
              desc: "The agent watches notes in real time and gently nudges physicians before they sign — preventing denials at the source.",
            },
            {
              title: "Self-Healing Enrichment (Simulated)",
              desc: "A demo of how an EHR integration could pull missing labs, history, and prior auths to re-score an incomplete claim. No live EHR connection — the enrichment is simulated.",
            },
            {
              title: "Dynamic Treasury Optimization",
              desc: "We don't just rank by denial risk. We prioritize claims based on how fast the payer actually pays — protecting cash flow.",
            },
          ].map((f) => (
            <div key={f.title} className="card p-8">
              <h3 className="font-semibold text-xl mb-3">{f.title}</h3>
              <p className="text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div id="position" className="max-w-6xl mx-auto px-6 pb-20 scroll-mt-20">
        <div className="card p-8 md:p-10 border-[var(--accent)]/30">
          <div className="text-[var(--accent)] text-sm tracking-[2px] font-medium mb-3">
            NOT ANOTHER SCRUBBER
          </div>
          <h3 className="text-2xl md:text-3xl font-semibold tracking-tight mb-4">
            A pre-submission decision layer — not a replacement for athenahealth or RapidClaims
          </h3>
          <p className="text-[var(--text-muted)] leading-relaxed max-w-3xl">
            Full RCM stacks like athenaOne and RapidClaims own the payer-rule libraries,
            NCCI scrubbing, EHR-native workflows, and denial recovery ops. ClaimGuard sits{" "}
            <strong className="text-[var(--text)]">upstream</strong> of them: it decides which
            claims a human should review before submission, using calibrated CMS CERT risk,
            a chart-note agent, and an expected-loss queue — then hands off to your scrubber
            and clearinghouse.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm font-medium">
            <span className="px-3 py-1.5 rounded-full bg-[var(--bg)] border border-[var(--border)]">
              ClaimGuard: score &amp; prioritize
            </span>
            <span className="text-[var(--text-muted)]">→</span>
            <span className="px-3 py-1.5 rounded-full bg-[var(--bg)] border border-[var(--border)]">
              Scrubber / athenaOne / RapidClaims: rules &amp; recovery
            </span>
            <span className="text-[var(--text-muted)]">→</span>
            <span className="px-3 py-1.5 rounded-full bg-[var(--bg)] border border-[var(--border)]">
              Clearinghouse: submit
            </span>
          </div>
        </div>
      </div>

      <div id="how" className="bg-[var(--bg-elevated)] border-y border-[var(--border)] py-16">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-center text-3xl font-semibold mb-10 tracking-tight">
            One platform. Three layers of intelligence.
          </h2>

          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">
                LAYER 01
              </div>
              <div className="font-semibold text-lg mb-2">Agentic Clinical Intelligence</div>
              <div className="text-sm text-[var(--text-muted)]">
                Agentic analysis, real-time corrections, policy compliance, and professional
                appeal drafting.
              </div>
            </div>
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">
                LAYER 02
              </div>
              <div className="font-semibold text-lg mb-2">ML Denial Prediction</div>
              <div className="text-sm text-[var(--text-muted)]">
                XGBoost model calibrated on real CMS CERT audit outcomes (ROC-AUC {rocAuc},
                isotonic-calibrated) scores improper-payment risk from coding signals.
              </div>
            </div>
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">
                LAYER 03
              </div>
              <div className="font-semibold text-lg mb-2">Financial Yield Management</div>
              <div className="text-sm text-[var(--text-muted)]">
                Prioritizes work not just by risk, but by how much cash is trapped and how
                fast each payer releases it.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-4xl font-semibold tracking-tight mb-4">Ready to see it in action?</h2>
        <p className="text-xl text-[var(--text-muted)] mb-8">
          Load the full realistic demo with one click. Explore every feature live.
        </p>

        <button
          type="button"
          onClick={launchDemo}
          className="btn btn-primary px-12 py-5 text-2xl font-semibold"
        >
          Launch Full Demo
        </button>

        <p className="text-xs text-[var(--text-muted)] mt-4">
          6 high-value claims · Real agent output · Treasury optimization enabled
        </p>
      </div>
    </div>
  );
}
