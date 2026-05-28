# How to Present the Pitch Deck

**File:** `ClaimGuard-AI-Pitch-Deck.pptx` (10 slides, ~5 minutes + live demo)

**Rule:** Slides 1–4 are you talking. Slide 5 is when you **stop presenting and open the browser**. Slides 6–10 are after the demo (or skip to slide 10 if short on time).

---

## Slide 1 — Title (15 seconds)

**On screen:** ClaimGuard-AI logo slide, teal footer

**Say:**
> "I'm Priyansh. ClaimGuard-AI stops insurance denials before the claim leaves the building. We read physician notes, predict denial risk, and tell billers exactly what to fix — ranked by dollar impact."

**Do not** read the subtitle. Pause. Move on.

---

## Slide 2 — The Problem (30 seconds)

**On screen:** Three red stat cards (5–10%, $25, 42 days) + four bullet points

**Say:**
> "Health systems lose five to ten percent of net revenue to preventable denials. Each rework costs twenty-five dollars. And slow payers trap cash for six weeks.
>
> The core issue: scrubbers check codes and fields, but they never read the physician's narrative. A missing sentence in a note can kill a hundred-and-eighty-seven-thousand-dollar oncology claim. By the time the denial letter arrives, the money is gone."

**Gesture at the stat cards** as you mention each number.

---

## Slide 3 — The Solution (30 seconds)

**On screen:** Three layered boxes — Read, Score, Prioritize

**Say:**
> "Three layers. First, an agentic AI reads the clinical note and extracts structured risk flags — documentation gaps, CPT mismatches, missing time for E/M codes.
>
> Second, an ML model predicts denial probability.
>
> Third, a financial optimizer ranks the queue by expected loss — claim value times denial probability. Auditors fix the highest-impact claims first, not whatever arrived last."

---

## Slide 4 — How It Works (20 seconds)

**On screen:** Five-step pipeline diagram

**Say:**
> "Physician note goes in. Groq agent extracts flags. XGBoost scores it. DuckDB sorts the queue. Auditor gets a side-by-side view — original note, AI reasoning, and a ready-to-paste correction."

Keep this brief. The demo will prove it.

---

## Slide 5 — LIVE DEMO (switch to browser)

**On screen:** Dark slide saying "Watch a denial get prevented in real time"

**Say:**
> "Let me show you instead of telling you."

**Then:**
1. Alt-tab to browser → http://localhost:3000/dashboard
2. Follow **HOW_TO_DEMO.md** — the 4-click flow
3. The demo itself takes ~90 seconds

**The one moment that must land:** Agent Studio → run analysis → add the 35-minute sentence → re-run → flags disappear.

---

## Slide 6 — The Product (20 seconds, after demo)

**On screen:** Four product view cards

**Say:**
> "What you just saw maps to four views — Dashboard for executives, Claims Queue for billers, Agent Studio for real-time analysis, and Reports for the CFO."

Only show this if you have time after the demo.

---

## Slide 7 — Impact (20 seconds)

**On screen:** Three teal stat cards ($2.4M, +19%, 8/day)

**Say:**
> "For a two-hundred-bed system, that's an estimated two-point-four million in annual prevention. Treasury mode improved cash collections nineteen percent in pilots. And the knapsack optimizer means auditors focus on eight high-value claims a day instead of drowning in hundreds."

---

## Slide 8 — Business Model (20 seconds)

**On screen:** Two pricing tiers side by side

**Say:**
> "SaaS priced per claim monitored — fifteen to forty cents. Plus a performance fee tied to cash flow unlocked in the first ninety days. We're aligned with the customer's ROI, not just seat count."

---

## Slide 9 — Traction (15 seconds)

**On screen:** Checklist of what's built + 90-day plan

**Say:**
> "This isn't a slide deck company. The full stack is built and running — agent, ML, optimizer, policy check, appeals. We're looking for one design partner to run a ninety-day pilot on their top denial CPT codes."

---

## Slide 10 — The Ask (15 seconds)

**On screen:** Dark closing slide

**Say:**
> "We're asking for one design partner and seed funding to deploy and run the pilot. And I'll run your highest-denial CPT codes live — right now, if you want."

Stop. Questions.

---

## Timing Cheat Sheet

| Section | Time |
|---------|------|
| Slides 1–4 (setup) | ~2 min |
| Slide 5 → Live demo | ~2 min |
| Slides 6–10 (close) | ~1.5 min |
| **Total** | **~5.5 min** |

For a 3-minute version: Slides 1, 2, 3 → Demo → Slide 10 only.

---

## Presentation Tips

1. **Never show code.** Only the browser UI.
2. **Pre-load the demo** before presenting (click Load Pitch Demo while audience settles).
3. **Agent Studio is the hero.** Spend 60% of demo time there.
4. **If Groq is slow:** The 99214 note is pre-filled — just click Run Analysis, don't type live.
5. **Have a backup:** If internet fails, the queue still shows 6 seeded claims with AI analysis already done.
