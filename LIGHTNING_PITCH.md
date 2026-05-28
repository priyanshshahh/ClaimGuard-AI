# 3-Minute Lightning Pitch Script

**When:** 4:00 PM · Bayer Co.Lab, 238 Main St, 2nd floor  
**Slides:** 5 max · `ClaimGuard-AI-Lightning-Pitch.pptx`  
**Demo:** Browser ready at http://localhost:3000/dashboard  

---

## BEFORE YOU GO ON STAGE (2 min prior)

1. Start backend + frontend (see HOW_TO_DEMO.md)
2. Open browser → Dashboard
3. Click **Load Pitch Demo** once (wait for toast)
4. Open Agent Studio in a second tab
5. Open slides from Google Drive folder OR local PPTX

---

## SLIDE 1 — Title + Problem (30 sec)

**Say:**
> "I'm Priyansh. Hospitals lose five to ten percent of net revenue to preventable claim denials. Each rework costs twenty-five dollars. And existing scrubbers never read the doctor's note — they only check codes and fields."

**Do not** read the bullet points. Point at the slide and move on.

---

## SLIDE 2 — Solution (30 sec)

**Say:**
> "ClaimGuard-AI is a pre-submission denial prevention engine. Our agent reads physician notes through the Nebius Token Factory API, extracts strict JSON risk flags, an XGBoost model predicts denial probability, and a bounded knapsack optimizer sorts the queue by expected financial loss. Billers fix the highest-dollar-risk claims first — before submission."

---

## SLIDE 3 — 24-Hour Progress + LIVE DEMO TRANSITION (15 sec)

**Say:**
> "In the last twenty-four hours we built the full stack — React frontend, FastAPI backend, Nebius integration, XGBoost, DuckDB optimizer, three product pages. Let me show you."

**→ Alt-tab to browser. Demo starts.**

---

## LIVE DEMO (90 sec) — THE MOST IMPORTANT PART

### A. Agent Studio (60 sec) — DO THIS FIRST

1. Go to **Agent Studio** tab (already open)
2. Say: *"This is a diabetes follow-up billed as a level-4 visit — CPT 99214 — with no time documented."*
3. Click **Run Agentic Analysis**
4. Point at **CO-16** badge: *"The agent flagged it instantly."*
5. Add to the note: `Spent 35 minutes counseling patient on diabetes management.`
6. Click **Run Agentic Analysis** again
7. Say: *"One sentence added. Denial flags gone. Before the claim was ever sent."*

### B. Claims Queue (20 sec)

1. Go to **Claims Queue**
2. Say: *"Six claims ranked by expected financial loss. Treasury Mode re-ranks by how slow the payer pays."*
3. Toggle Treasury Mode briefly

### C. Done

Say: *"That's the product."* Alt-tab back to slides.

---

## SLIDE 4 — Future Directions (20 sec)

**Say:**
> "Next: a ninety-day pilot with a regional health system, EHR integration, and scaling to a fully autonomous financial clearinghouse. We're applying for the Global Sprint in November."

---

## SLIDE 5 — Close (10 sec)

**Say:**
> "ClaimGuard-AI prevents denials before they happen. Happy to run your highest-denial CPT codes live after. Thank you."

---

## TIMING

| Section | Time |
|---------|------|
| Slides 1–2 | 60 sec |
| Slide 3 + Demo | 105 sec |
| Slides 4–5 | 30 sec |
| **Total** | **~3 min** |

---

## RULES REMINDER

- Do NOT pitch a pre-existing company
- Do NOT show code — browser UI only
- Do NOT exceed 5 slides or 3 minutes
- DO mention Nebius (required for attendees who used credits)

---

## IF DEMO FAILS

Say: *"Backend is seeding — let me show the pre-loaded queue."*  
Go to Claims Queue (demo data persists in session).  
Show the 99214 row with CO-16 flags in the table.

---

## UPLOAD CHECKLIST

- [ ] Upload `ClaimGuard-AI-Lightning-Pitch.pptx` to Google Drive slides folder
- [ ] Upload `PROJECT_WRITEUP.md` (or export as PDF) to writeup folder
- [ ] Attend 4 PM pitch if you used Nebius credits
