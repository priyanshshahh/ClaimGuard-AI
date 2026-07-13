# ClaimGuard-AI

Pre-submission claim denial-risk engine for healthcare revenue cycle teams: an ML model trained on **real CMS audit data** scores every claim, an LLM agent reads the physician note for documentation gaps, and a knapsack optimizer orders the auditor queue by expected financial loss.

Started as an AIxBio hackathon project (Bayer Co.Lab, May 2026); the model layer has since been rebuilt on real data with honest, reproducible evaluation.

## The model is trained on real data

**Dataset:** [Medicare Fee-for-Service Comprehensive Error Rate Testing (CERT)](https://data.cms.gov/quality-of-care/medicare-fee-for-service-comprehensive-error-rate-testing) — a public CMS program that draws a random sample of FFS claims each year and has independent reviewers audit whether each claim was paid properly. ~160-185k claim lines per report year, no authentication required.

**Label (real, not synthetic):** `Review Decision == "Disagree"` — the CERT reviewer determined the claim was improperly paid. The dominant causes (insufficient documentation, medical necessity, incorrect coding) are the same failure modes that drive payer denials, which is why we use it as a documented **proxy** for denial risk. Appeals that were overturned count as properly paid.

**Split (temporal, leakage-free):** train on report years 2021-2023, validate on 2024, test on 2025. All categorical encodings (smoothed target rates per HCPCS code, provider type, type of bill) are fitted on the training years only.

### Results (from the committed run in `backend/models/metrics.json`)

Test = 2025 report year, n = 163,940 claim lines, base rate 14.1%:

| Model | ROC-AUC | PR-AUC | Brier | Log loss |
|---|---|---|---|---|
| Logistic regression (baseline) | 0.740 | 0.283 | 0.1131 | 0.369 |
| XGBoost | 0.745 | 0.302 | 0.1108 | 0.361 |
| **XGBoost + isotonic calibration (served)** | **0.745** | **0.295** | **0.1096** | **0.358** |

Validation = 2024, n = 185,349, base rate 15.8%: served model ROC-AUC 0.735, PR-AUC 0.310, Brier 0.1203.

Calibration matters here because probabilities are multiplied by claim value to rank work. On the 2025 test year the served model's reliability curve tracks observed rates closely in the low-probability mass (e.g. predicted 0.012 → observed 0.015; predicted 0.083 → observed 0.103); full 10-bin curves for every model/split are in `metrics.json`.

These are honest numbers for 5 raw claim attributes. The public CERT file has no chart notes, no payer identity, and no dollar amounts — a production system sitting on an EHR would have far richer features.

### Reproduce

```bash
python scripts/train.py            # downloads CERT 2021-2025 (~67 MB), trains, evaluates
```

Deterministic seed, artifacts written to `backend/models/` (model, calibrator, feature maps, metrics). Experiment tracking via Weights & Biases is optional: offline by default, `WANDB_API_KEY` to sync, `WANDB_MODE=disabled` to turn off.

## How a claim is scored

1. **Model probability (statistical):** calibrated P(improper payment) from the claim's CPT/HCPCS code and claim-type attributes.
2. **Agent findings (LLM):** Groq (or Nebius) reads the de-identified chart note and returns strict-schema flags — documentation complete, medical necessity present, CPT/ICD mismatch, predicted CARC codes, and a paste-ready correction draft.
3. **Documented heuristic uplift:** flagged documentation problems add fixed, capped increments to the model probability (constants in `backend/model.py`). This layer is a business rule, not model output — the API returns `model_base_probability` and `denial_probability` separately so the two are never conflated.
4. **Queue optimization:** expected loss = claim value x probability; a bounded knapsack selects the best set under auditor capacity, and a treasury mode weights by payer payment speed.

## Honest limitations

- CERT measures *improper payment on audit*, not payer denials; the label is a documented proxy.
- The agent-flag uplift constants are heuristics, reported separately from model output.
- PHI scrubbing (`backend/deidentify.py`) is regex-based and best-effort — fine for a demo, **not** a certified HIPAA de-identification pipeline. Do not send real patient data.
- Demo claims seeded via `/api/seed-demo` are synthetic and labeled `is_demo: true` everywhere.
- The `/api/fhir/claim` endpoint is a structure-mapping demo only.

## Quick start

```bash
# Backend (Python 3.12)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example backend/.env        # GROQ_API_KEY optional; scoring works without it
cd backend && uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:3000/dashboard
```

Or `docker compose up` for both.

```bash
cd backend && pytest tests/ -q     # 62 tests
```

## Stack

- **Model:** XGBoost + isotonic calibration; scikit-learn baseline; W&B tracking
- **Backend:** FastAPI, DuckDB (single store), strict-Pydantic LLM extraction (Groq / Nebius)
- **Frontend:** Next.js 16, Tailwind, Recharts
- **CI:** ruff + pytest + frontend build (GitHub Actions)

## License

MIT
