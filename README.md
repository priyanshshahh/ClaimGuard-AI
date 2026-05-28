# ClaimGuard-AI

Agentic pre-submission financial risk engine for healthcare revenue cycle management.

Prevents insurance claim denials **before submission** by reading physician notes, predicting denial probability, and prioritizing auditor work by expected financial loss.

## Hackathon Submission — AIxBio @ Bayer Co.Lab (May 2026)

| Deliverable | File |
|-------------|------|
| Lightning pitch deck (5 slides) | `ClaimGuard-AI-Lightning-Pitch.pptx` |
| Project write-up | `PROJECT_WRITEUP.md` |
| 3-min pitch script | `LIGHTNING_PITCH.md` |
| Demo walkthrough | `HOW_TO_DEMO.md` |

## Quick Start

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add NEBIUS_API_KEY
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000/dashboard** → **Load Pitch Demo**

## Stack

- **Frontend:** Next.js 16, React, Tailwind, Recharts
- **Backend:** FastAPI, Nebius Token Factory (Gemma 3 27B), XGBoost, DuckDB
- **Agent:** Strict Pydantic JSON extraction with CO-11/CO-16/99214 rules

## License

MIT — Hackathon project
