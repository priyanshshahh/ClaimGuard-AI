# ClaimGuard-AI — 3-Minute Investor Pitch Script

## Slide 1: Opening (15 sec)
> "ClaimGuard-AI is an agentic AI financial risk engine that autonomously prevents healthcare insurance denials before they occur. We protect revenue at the source — not after the denial letter arrives."

## Slide 2: Problem (30 sec)
> "Healthcare operates on razor-thin margins. Systems bleed 5 to 10 percent of net revenue to preventable denials. Reworking a single denied claim costs twenty-five dollars and traps cash for weeks. Legacy scrubbers only check structured fields — they can't read the physician's narrative."

## Slide 3: Solution (30 sec)
> "Our agent reads unstructured clinical notes, extracts typed risk flags via Groq, feeds them into XGBoost for denial probability, and sorts the queue by expected financial loss using a bounded knapsack optimizer. Staff work the highest-value claims first."

## Live Demo (90 sec) — DO NOT SHOW CODE

### Step 1: Dashboard
- Click **Load Pitch Demo**
- Point to KPI cards: pipeline liquidity, revenue at risk

### Step 2: Claims Queue
- Show priority table sorted by EL
- Toggle **Treasury Mode** — explain slow payers (BCBS 42 days) jump priority

### Step 3: Agent Studio (THE MONEY SHOT)
- Pre-loaded CPT **99214** note missing time documentation
- Click **Run Agentic Analysis** — Pᵢ spikes, CO-16 flag appears
- Add: *"spent 35 minutes counseling patient on diabetes management"*
- Re-run — Pᵢ drops near zero
- Say: *"That's a denial prevented before submission."*

### Step 4: Reports
- Show denial code breakdown chart
- Click **Export PDF**

## Slide 4: Moat (20 sec)
> "Experian guesses from historical metadata. CombineHealth overwhelms staff with every flag. We combine agentic text reading with deterministic financial prioritization."

## Slide 5: Business Model (15 sec)
> "Tiered SaaS on claim volume plus a performance fee tied to cash flow unlocked."

## Close (10 sec)
> "We're seeking a design partner health system for a 90-day pilot. Happy to run your highest-denial CPT codes live."

---

## Demo Scenarios (backup)

| Scenario | CPT | Trick | Expected |
|----------|-----|-------|----------|
| E/M Level Mismatch | 99214 | Omit time documentation | CO-16, high Pᵢ |
| E/M Fix | 99214 | Add "35 minutes counseling" | Pᵢ → near 0 |
| Ortho High-Value | 27447 | Complete TKA note | Low Pᵢ, low EL |
| Cardiology | 93000 + routine exam ICD | ECG without cardiac indication | CO-11 flag |
