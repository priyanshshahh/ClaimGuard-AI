# ClaimGuard-AI — Project Write-Up (Hackathon Submission)

**Team:** Priyansh Shah · Stony Brook University  
**Event:** AIxBio Hackathon @ Bayer Co.Lab · May 28, 2026  
**Format:** 3-minute lightning pitch · Maximum 5 slides  

---

## 1. Problem Statement

Healthcare revenue cycle teams lose **5–10% of net revenue** to preventable insurance claim denials. Each denied claim costs approximately **$25 to rework** and traps cash for 30–60 days.

Existing claim scrubbers validate structured fields (CPT codes, ICD-10 codes, demographics) but **cannot read unstructured physician narratives**. A missing sentence — such as time documentation for a Level 4 E/M visit (CPT 99214) — triggers denials that are entirely preventable at the pre-submission stage.

Manual auditor review does not scale. Teams need an AI co-pilot that reads clinical notes, predicts denial risk, and prioritizes work by **financial impact**.

---

## 2. Solution — ClaimGuard-AI

ClaimGuard-AI is an **agentic pre-submission financial risk engine** for healthcare revenue cycle management. It replaces static rule-based scrubbers with a three-layer intelligence stack:

| Layer | Technology | Function |
|-------|-----------|----------|
| **Agentic Extraction** | Nebius Token Factory (Gemma 3 27B) | Reads physician notes, outputs strict JSON risk flags |
| **Quantitative Scoring** | XGBoost Classifier | Predicts denial probability Pᵢ from clinical + payer features |
| **Financial Optimization** | DuckDB + Bounded Knapsack | Sorts queue by Expected Financial Loss ELᵢ = Vᵢ × Pᵢ |

### Strict JSON Schema (Pydantic `strict=True`)

Every agent response includes:
- `documentation_complete` (0/1)
- `clinical_justification_present` (0/1)
- `procedure_mismatch_flag` (0/1)
- `predicted_denial_codes` (CO-11, CO-16, CO-50, CO-97)
- `agent_correction_draft` (ready-to-paste fix text)

### Medical Necessity Rules Engine

The agent evaluates notes against:
- **CO-11:** ICD-10 inconsistent with CPT procedure
- **CO-16:** Missing information / demographics / signatures
- **CPT 99214:** Requires moderate complexity OR 30–39 minutes documented
- **CO-50 / CO-97:** Medical necessity and E/M level mismatch

---

## 3. Architecture

```
Physician Note + CPT/ICD/Payer/Value
        ↓
Nebius Token Factory API (Llama 3.1 8B Instruct)
  → Strict JSON clinical flags
        ↓
XGBoost Classifier (scale_pos_weight for imbalanced denials)
  → Denial probability Pᵢ
        ↓
Expected Loss ELᵢ = Vᵢ × Pᵢ
        ↓
DuckDB analytical sort + Bounded Knapsack (capacity K/day)
        ↓
Next.js Frontend (Auditor Worklist · Agent Studio · Executive Dashboard)
```

### Backend (FastAPI)
- `POST /api/analyze-claim` — Full agent + ML pipeline
- `GET /api/priority-queue` — Knapsack-sorted worklist
- `GET /api/dashboard-metrics` — Executive KPIs + denial code breakdown
- `POST /api/check-policy` — Payer policy RAG
- `POST /api/generate-appeal` — Auto-appeal letter generation
- `POST /api/seed-demo` — Load 6 realistic demo claims

### Frontend (Next.js 16)
- **Dashboard** — KPI cards, Load Pitch Demo
- **Claims Queue** — Bounded knapsack table, Treasury Mode toggle, resolve drawer
- **Agent Studio** — Live note analysis, Pᵢ dial, policy check, appeals
- **Reports** — Denial code charts, payer trends, PDF/CSV export

---

## 4. Infrastructure & Cost Model

| Component | Provider | Purpose |
|-----------|----------|---------|
| Production LLM | **Nebius Token Factory** | Llama 3.1 8B — $0.02/M input, $0.06/M output tokens |
| Development IDE | Cursor / Grok Build | Free-tier code scaffolding |
| Backend hosting | Render (planned) | FastAPI deployment |
| Frontend hosting | Vercel (planned) | Next.js deployment |
| Database | DuckDB (local) + Supabase (planned) | Analytics + persistence |

Nebius credits are used **exclusively at inference time** in the FastAPI backend. Development and code generation consume zero Nebius budget.

---

## 5. 24-Hour Hackathon Progress

Built in 24 hours at Bayer Co.Lab:

- [x] Full-stack multi-page React + FastAPI application
- [x] Nebius Token Factory API integration with strict JSON extraction
- [x] XGBoost denial classifier with imbalanced learning
- [x] DuckDB-powered bounded knapsack financial optimizer
- [x] Three product pages (Worklist, Agent Studio, Executive Dashboard)
- [x] Six realistic demo claims from major payers
- [x] Policy check and auto-appeals generator
- [x] Executive PDF/CSV export
- [x] End-to-end API test suite passing

---

## 6. Live Demo Script (90 seconds)

1. **Dashboard** → Click "Load Pitch Demo" (6 claims analyzed)
2. **Agent Studio** → Run analysis on CPT 99214 note (missing time) → CO-16 flag appears
3. Add *"Spent 35 minutes counseling patient"* → Re-run → flags disappear
4. **Claims Queue** → Show knapsack-prioritized table → Toggle Treasury Mode
5. **Reports** → Export executive PDF

---

## 7. Future Directions

1. **90-day pilot** with a regional health system measuring recovered revenue
2. **Supabase persistence** and multi-tenant auth
3. **EHR integration** via FHIR R4 endpoints (stub already implemented)
4. **Expand rules engine** across all medical specialties
5. **Global Sprint Hackathon (November 2026)** — production deployment at scale

---

## 8. Repository Structure

```
ClaimGuard-AI/
├── backend/          FastAPI + agent + XGBoost + DuckDB
├── frontend/         Next.js multi-page app
├── scripts/          Pitch deck generators
├── HOW_TO_DEMO.md    Step-by-step demo guide
├── HOW_TO_PRESENT.md Lightning pitch script
└── PROJECT_WRITEUP.md  This document
```

---

## 9. Running Locally

```bash
# Backend
cd backend && source venv/bin/activate && pip install -r requirements.txt
python main.py

# Frontend
cd frontend && npm run dev

# Open http://localhost:3000/dashboard
```

Requires `NEBIUS_API_KEY` in `backend/.env`. Groq key optional as fallback.

---

*Submitted for AIxBio Hackathon evaluation · NVIDIA / Nebius Global Sprint consideration · May 2026*
