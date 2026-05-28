# How to Run the Pitch Demo (Simple Guide)

You only need **two terminals running** and **one browser tab**. The whole demo takes about **2 minutes**.

---

## Before You Start

**Terminal 1 — Backend:**
```bash
cd /Users/priyansh/Desktop/aihealthcar/ClaimGuard-AI/backend
source venv/bin/activate
python main.py
```
Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 — Frontend:**
```bash
cd /Users/priyansh/Desktop/aihealthcar/ClaimGuard-AI/frontend
npm run dev
```
Wait until you see: `Local: http://localhost:3000`

**Open in browser:** http://localhost:3000/dashboard

---

## The Demo in 4 Clicks (What Each One Does)

### Click 1 — Load Pitch Demo
**Where:** Sidebar button **"Load Pitch Demo"** (bottom left) OR Dashboard button **"Load Pitch Demo"**

**What happens behind the scenes:**
- Backend wipes the queue and loads 6 realistic hospital claims
- For each claim, the Groq AI agent reads the physician note
- XGBoost calculates denial probability
- DuckDB stores everything and sorts by Expected Financial Loss

**What you say:**
> "I'm loading six real-world claims from a regional health system — oncology, cardiology, orthopedics, and a routine office visit. Watch the AI analyze each one."

**What you see:** Toast notification — *"Demo Ready: 6 Claims Loaded"*

---

### Click 2 — Agent Studio (THE MAIN EVENT)
**Where:** Sidebar → **Agent Studio**

**What's already on screen:**
- A diabetes follow-up note (CPT **99214**)
- The note deliberately says *"Brief visit, no time documented"*

**What you do:**
1. Click **"Run Agentic Analysis"**
2. Point to the results:
   - Red denial code badges: **CO-16**, **CO-97**
   - AI explanation: *"Lacks documentation of time spent..."*
   - Correction draft box: ready-to-paste fix text

**What you say:**
> "This is a level-4 office visit billed without time documentation. The AI flagged it instantly — this would get denied."

3. **Scroll to the text box.** At the end of the note, add this sentence:
   ```
   Spent 35 minutes counseling patient on diabetes management, medication adherence, and lifestyle modifications.
   ```
4. Click **"Run Agentic Analysis"** again

**What you see:**
- Denial code badges **disappear**
- AI says the 35 minutes satisfies CPT 99214 requirements

**What you say:**
> "The biller adds one sentence. The denial disappears before the claim is ever submitted. That's the product."

---

### Click 3 — Claims Queue
**Where:** Sidebar → **Claims Queue**

**What you see:**
- A table of all 6 claims sorted by Expected Financial Loss (highest $ at risk on top)
- Columns: claim value, denial probability, agent flags (✓/❌), denial codes
- The **99214 claim** shows ❌ in the Doc column and CO-16 in codes

**What you do:**
1. Click any high-value row (e.g. CLM-ONC-3914) — the right panel opens
2. Show: original chart text, AI reasoning, correction draft
3. Click **"Switch to Treasury Optimization Mode"** button (top right)

**What you say:**
> "Auditors don't review claims in arrival order. We sort by expected financial loss. Treasury Mode goes further — a $67K claim from BCBS, which pays in 42 days, jumps above a faster-paying Medicare claim because that trapped cash hurts more."

---

### Click 4 — Reports
**Where:** Sidebar → **Reports**

**What you see:**
- KPI cards: pipeline liquidity (~$388K), revenue at risk
- Bar chart: denial code breakdown (CO-16, CO-97)
- Line chart: payer denial trends

**What you do:** Click **Export PDF**

**What you say:**
> "The CFO sees exactly where revenue is leaking — by denial code, by payer — and can export this for the board."

---

## Optional: Show These If You Have Time

| Feature | Where | What to click |
|---------|-------|---------------|
| Policy check | Agent Studio → after running analysis | **Run Payer Policy Check** |
| Auto-appeal | Agent Studio → after running analysis | **Generate Appeal Letter** |
| New claim | Claims Queue → **New Claim** | Fill form → **Run Full Analysis** |
| Self-healing | Agent Studio | **Self-Heal: Fetch Missing Data** |

---

## If Something Breaks

| Problem | Fix |
|---------|-----|
| "Analysis failed" toast | Backend isn't running — start Terminal 1 |
| Empty queue | Click **Load Pitch Demo** again |
| Port 8000 in use | Something already running — just open localhost:3000 |
| Blank dashboard | Click **Load Pitch Demo**, wait 10 seconds |

---

## The One Sentence Summary

> ClaimGuard-AI reads physician notes, predicts which claims will be denied, ranks them by dollar impact, and tells billers exactly what to fix — before submission.
