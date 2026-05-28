# ClaimGuard-AI - Quick Start Guide

## 1. Backend (5 minutes)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

Backend will be available at: **http://localhost:8000**

Test it at: http://localhost:8000/docs

## 2. Frontend (Recommended)

The modern professional multi-page SaaS experience is at:

```bash
cd frontend
npm run dev
```

Then open **http://localhost:3000**

This is the full product with:
- Dashboard
- Claims Queue (with Treasury Optimization)
- Agent Studio (Ambient Auditing, Policy Checks, Auto-Appeals)
- Reports
- Settings

The old single-file HTML now redirects to this new app.

## 3. How to Use

1. Click **"Analyze New Claim"**
2. Fill in the form (or use pre-filled demo data)
3. Click "Run Agentic Analysis"
4. Watch the agent generate clinical corrections
5. View prioritized queue sorted by Expected Loss

## API Endpoints

- POST /api/analyze-claim
- GET /api/priority-queue  
- GET /api/dashboard-metrics

## Notes

- Groq API key is already configured in `.env`
- Model is pre-trained on synthetic data for demo
- For production, replace with real training data + Supabase

Built during AIxBio Hackathon at Bayer Co.Lab - May 28, 2026