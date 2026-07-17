"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { API_URL, apiFetch } from "../lib/api";

export default function LandingPage() {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    const hasSeenTour = localStorage.getItem('hasSeenOnboarding');
    if (!hasSeenTour) {
      // Show after a short delay on first visit
      const timer = setTimeout(() => setShowOnboarding(true), 1800);
      return () => clearTimeout(timer);
    }
  }, []);
  const launchDemo = async () => {
    try {
      const data = await apiFetch("/api/seed-demo", { method: "POST" });
      
      toast.success(`Demo Ready: ${data.seeded} Claims Loaded`, { 
        description: `$${Math.round(data.total_revenue_at_risk / 1000)}k revenue at risk — Treasury optimization active` 
      });

      // Small delay so user sees the toast
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 900);
    } catch (e) {
      toast.error("Could not connect to backend", { 
        description: "Please run the backend: cd backend && python main.py" 
      });
    }
  };

  const goToStudio = () => window.location.href = "/studio";

  // Auto-launch if ?demo=true in URL (for quick pitch links)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "true") {
      launchDemo();
    }
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      {/* Top Nav */}
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
            <a href="#features" className="text-[var(--text-muted)] hover:text-[var(--text)]">Features</a>
            <a href="#how" className="text-[var(--text-muted)] hover:text-[var(--text)]">How it Works</a>
            <button onClick={launchDemo} className="btn btn-primary px-5 py-2 text-sm">Launch Live Demo</button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-block px-4 py-1.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] text-sm font-medium tracking-widest mb-6">
          PRE-SUBMISSION REVENUE PROTECTION
        </div>

        <h1 className="text-7xl font-semibold tracking-[-4.5px] leading-[0.95] mb-6">
          Protect every dollar<br />before the claim is sent.
        </h1>

        <p className="max-w-2xl mx-auto text-2xl text-[var(--text-muted)]">
          A platform that combines real-time agentic note analysis, payer policy intelligence, and cash-flow optimized claim prioritization on a model trained on real CMS audit data.
        </p>

        <div className="mt-10 flex items-center justify-center gap-4">
          <button 
            onClick={launchDemo} 
            className="btn btn-primary px-10 py-4 text-xl font-semibold"
          >
            Launch Live Demo
          </button>
          <button 
            onClick={goToStudio} 
            className="btn btn-ghost px-8 py-4 text-xl"
          >
            Explore the Agent
          </button>
        </div>

        <div className="mt-6 flex items-center justify-center gap-4 text-sm">
          <button onClick={() => window.location.href = "/reports"} className="text-[var(--text-muted)] hover:text-[var(--text)] underline">View Reports & History</button>
          <span className="text-[var(--text-muted)]">·</span>
          <button 
            onClick={() => {
              localStorage.removeItem('hasSeenOnboarding');
              window.location.reload();
            }} 
            className="text-[var(--text-muted)] hover:text-[var(--text)] underline"
          >
            Replay Welcome Tour
          </button>
        </div>

        <p className="mt-4 text-xs text-[var(--text-muted)]">No login • Full backend connected • Ready for investor demo</p>
      </div>

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[100] p-4">
          <div className="bg-[var(--bg-elevated)] rounded-3xl max-w-lg w-full p-8 border border-[var(--border)]">
            <h2 className="text-2xl font-semibold mb-2">Welcome to ClaimGuard AI</h2>
            <p className="text-[var(--text-muted)] mb-6">Here's how to get the most out of your demo in the next 60 seconds:</p>
            
            <ol className="space-y-4 text-sm mb-8">
              <li className="flex gap-3"><span className="font-mono text-[var(--accent)]">02</span> Open <strong>Dashboard</strong> → click <strong>Load Pitch Demo</strong>.</li>
              <li className="flex gap-3"><span className="font-mono text-[var(--accent)]">03</span> Go to <strong>Claims Queue</strong> and toggle <strong>Treasury Mode</strong>.</li>
              <li className="flex gap-3"><span className="font-mono text-[var(--accent)]">04</span> Open <strong>Agent Studio</strong> for live ambient auditing and appeals.</li>
              <li className="flex gap-3"><span className="font-mono text-[var(--accent)]">05</span> Visit <strong>Reports</strong> to export PDF/CSV executive reports.</li>
            </ol>

            <div className="flex gap-3">
              <button 
                onClick={() => {
                  localStorage.setItem('hasSeenOnboarding', 'true');
                  setShowOnboarding(false);
                }} 
                className="btn btn-ghost flex-1"
              >
                Skip Tour
              </button>
              <button 
                onClick={() => {
                  localStorage.setItem('hasSeenOnboarding', 'true');
                  setShowOnboarding(false);
                  // Optionally auto-launch demo
                }} 
                className="btn btn-primary flex-1"
              >
                Got it — Start Exploring
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Financial Intelligence Teaser (Phase 6) */}
      <div className="max-w-6xl mx-auto px-6 pb-16 -mt-8">
        <div className="text-center mb-8">
          <div className="text-sm text-[var(--accent)] font-medium tracking-widest">DYNAMIC TREASURY OPTIMIZATION</div>
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
            <div className="text-4xl font-semibold text-[var(--primary)]">0.745</div>
            <div className="mt-1 font-medium">Denial Model ROC-AUC</div>
            <div className="text-xs text-[var(--text-muted)] mt-2">CMS CERT 2025 holdout — real offline eval, not a pilot</div>
          </div>
        </div>

        <div className="text-center mt-8">
          <button onClick={() => window.location.href = "/reports"} className="btn btn-ghost text-sm">
            View full Treasury vs Risk analytics in Reports →
          </button>
        </div>
      </div>

      {/* Trust Bar */}
      <div className="border-y border-[var(--border)] bg-[var(--bg-elevated)] py-6">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-center gap-x-4 text-sm text-[var(--text-muted)] text-center">
          <div>Built for provider-side revenue-cycle teams — a solo portfolio project on public CMS CERT data, not a deployed vendor product.</div>
        </div>
      </div>

      {/* Features Section */}
      <div id="features" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <div className="text-[var(--accent)] text-sm tracking-[2px] font-medium">WHY CLAIMGUARD IS DIFFERENT</div>
          <h2 className="text-4xl font-semibold tracking-tight mt-3">Beats every existing solution</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              title: "Ambient Pre-Signature Auditing",
              desc: "The agent watches notes in real time and gently nudges physicians before they sign — preventing denials at the source."
            },
            {
              title: "Self-Healing Enrichment (Simulated)",
              desc: "A demo of how an EHR integration could pull missing labs, history, and prior auths to re-score an incomplete claim. No live EHR connection — the enrichment is simulated."
            },
            {
              title: "Dynamic Treasury Optimization",
              desc: "We don't just rank by denial risk. We prioritize claims based on how fast the payer actually pays — protecting cash flow."
            }
          ].map((f, i) => (
            <div key={i} className="card p-8">
              <h3 className="font-semibold text-xl mb-3">{f.title}</h3>
              <p className="text-[var(--text-muted)] leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How it Works */}
      <div id="how" className="bg-[var(--bg-elevated)] border-y border-[var(--border)] py-16">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-center text-3xl font-semibold mb-10 tracking-tight">One platform. Three layers of intelligence.</h2>
          
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">LAYER 01</div>
              <div className="font-semibold text-lg mb-2">Agentic Clinical Intelligence</div>
              <div className="text-sm text-[var(--text-muted)]">Nebius-powered agentic analysis, real-time corrections, policy compliance, and professional appeal drafting.</div>
            </div>
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">LAYER 02</div>
              <div className="font-semibold text-lg mb-2">ML Denial Prediction</div>
              <div className="text-sm text-[var(--text-muted)]">XGBoost model calibrated on real CMS CERT audit outcomes (ROC-AUC 0.745, isotonic-calibrated) scores denial probability from coding and payer signals.</div>
            </div>
            <div>
              <div className="text-[var(--primary)] font-mono text-sm tracking-widest mb-2">LAYER 03</div>
              <div className="font-semibold text-lg mb-2">Financial Yield Management</div>
              <div className="text-sm text-[var(--text-muted)]">Prioritizes work not just by risk, but by how much cash is trapped and how fast each payer releases it.</div>
            </div>
          </div>
        </div>
      </div>

      {/* Final CTA */}
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-4xl font-semibold tracking-tight mb-4">Ready to see it in action?</h2>
        <p className="text-xl text-[var(--text-muted)] mb-8">Load the full realistic demo with one click. Explore every feature live.</p>
        
        <button 
          onClick={launchDemo} 
          className="btn btn-primary px-12 py-5 text-2xl font-semibold"
        >
          Launch Full Investor Demo
        </button>
        
        <p className="text-xs text-[var(--text-muted)] mt-4">6 high-value claims • Real agent output • Treasury optimization enabled</p>
      </div>
    </div>
  );
}
