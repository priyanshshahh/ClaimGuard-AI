"use client";

import { useState } from 'react';
import { toast } from 'sonner';

export default function Settings() {
  const [threshold, setThreshold] = useState(0.65);
  const [demoMode, setDemoMode] = useState(true);

  const saveSettings = () => {
    toast.success("Settings saved", { description: "Changes applied to current session" });
  };

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-[var(--text-muted)]">Configure how ClaimGuard protects your revenue cycle</p>
      </div>

      <div className="card p-8 space-y-8">
        <div>
          <label className="block text-sm font-medium mb-2">Minimum Agent Confidence for Auto-Accept</label>
          <input 
            type="range" 
            min="0.5" 
            max="0.95" 
            step="0.05" 
            value={threshold} 
            onChange={e => setThreshold(parseFloat(e.target.value))} 
            className="w-full accent-[var(--primary)]" 
          />
          <div className="text-right text-sm font-mono mt-1">{(threshold * 100).toFixed(0)}%</div>
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border)] pt-6">
          <div>
            <div className="font-medium">Demo Mode</div>
            <div className="text-sm text-[var(--text-muted)]">Use pre-seeded realistic health system data for presentations</div>
          </div>
          <button 
            onClick={() => { setDemoMode(!demoMode); toast.info(demoMode ? "Demo mode disabled" : "Demo mode enabled"); }}
            className={`px-4 py-1.5 rounded-2xl text-sm font-medium transition ${demoMode ? 'bg-[var(--accent)] text-white' : 'bg-[var(--bg)] border'}`}
          >
            {demoMode ? "Enabled" : "Disabled"}
          </button>
        </div>

        <div className="border-t border-[var(--border)] pt-6">
          <div className="font-medium mb-2">EHR Integration</div>
          <div className="text-sm bg-[var(--bg)] p-4 rounded-2xl border text-[var(--text-muted)]">
            FHIR R4 endpoint connected (simulated). Real Epic/Cerner integration available in production deployment.
          </div>
        </div>
      </div>

      <button onClick={saveSettings} className="btn btn-primary w-full py-3 text-base">Save Configuration</button>
    </div>
  );
}
