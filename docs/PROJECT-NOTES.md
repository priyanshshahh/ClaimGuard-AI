# Project Notes — real-model rebuild (July 2026)

Engineering log for the `real-model` branch: what changed, why, and what a reviewer should know is real vs. heuristic.

## Why the rebuild

The hackathon version trained XGBoost on `numpy.random` synthetic data at every server start and blended it with LLM guesses — impressive demo, indefensible in an interview. This branch replaces every fabricated number with a measured one.

## Dataset decision

Requirements: real claims with real adjudication outcomes, public, no auth, big enough to matter.

Chosen: **CMS Medicare FFS Comprehensive Error Rate Testing (CERT)**, report years 2021-2025 (~860k claim lines total). Each line is a genuinely audited claim with a reviewer decision (`Agree`/`Disagree` with payment) and an error category. Rejected alternatives: SyntheticMass/Synthea (synthetic), CMS SAF/LDS (requires DUA), payer denial dumps (not public).

**Label:** `Disagree` = improper payment (14-20% base rate depending on year). `Agree` + appeal-`Overturned` = 0. This is a *proxy* for denial risk and is documented as such everywhere — the error categories (insufficient documentation 45-50% of errors, medical necessity, incorrect coding) are the same failure modes payers deny on.

## Modeling choices

- **Temporal split** (train 2021-2023 / val 2024 / test 2025): no claim overlap across report years, so no group leakage; also the honest deployment scenario — predict next year from past years.
- **Features:** only 5 raw columns exist (Part, HCPCS, provider type, type of bill, DRG). Engineered: smoothed target encodings (m=50) fitted on train years only, frequency counts, category indices. Unseen levels fall back to the training prior.
- **Models:** logistic regression baseline vs XGBoost (early stopping on val), then isotonic calibration fitted on val. Calibration is the point — probabilities get multiplied by dollars.
- **Real numbers** (test 2025, n=163,940): served model ROC-AUC 0.745, PR-AUC 0.295 vs 0.141 base rate, Brier 0.1096. Modest and honest; the feature set is thin by construction of the public file.
- Committed artifacts (~800 KB) in `backend/models/` so serving never retrains; `scripts/train.py` reproduces them deterministically (seed 42).

## Serving design

`model_base_probability` (calibrated model output) and `denial_probability` (after documented heuristic uplifts for agent-flagged documentation problems: +0.15 doc missing, +0.10 no justification, +0.12 CPT/ICD mismatch, capped at 0.97) are separate API fields. The uplifts are business rules in code, not model claims. CERT has no note text, so the agent flags cannot be model features — this is the honest way to combine the two signals.

## Bugs found and fixed along the way

1. **CORS never worked for previews:** Starlette exact-matches `allow_origins`, so `https://*.vercel.app` matched nothing. Fixed with `allow_origin_regex` + regression tests (including a `foo.vercel.app.evil.com` lookalike test).
2. **Dual-store drift:** claims lived in an in-memory dict *and* DuckDB, synced by hand. Now DuckDB is the only store.
3. **DuckDB migration footgun:** re-running `ALTER TABLE ADD COLUMN IF NOT EXISTS ... DEFAULT` on every connect silently reset column values on reconnect. Caught by the new store tests; migration now checks `PRAGMA table_info` first.
4. **Strict schema rejected real LLM output:** live Groq verification showed the model returns JSON booleans for 0/1 flags, `null` for optional strings, and `1` for confidence — strict Pydantic rejected the payload and *every* analysis silently fell back to a canned response. Fixed with targeted before-validators; regression tests added.

## Trust & safety

- `backend/deidentify.py` scrubs SSN/phone/email/MRN/DOB/dates/cued names/addresses before any LLM call, at the single agent-layer choke point. Documented as best-effort, not certified HIPAA de-identification.
- Demo data is labeled `is_demo=true` in the store and API responses; the FHIR endpoint says `demo: true` explicitly.

## Verification performed (all real runs)

- `pytest`: 62 tests green (schema, scrubber, optimizer/knapsack properties, store, model serving, training pipeline on a 2000-row real CERT fixture, API routes, CORS).
- Live Groq call: chest-pain note → valid `ClinicalAnalysis`, sensible CO-50 flag (surfaced bug #4).
- Full training run on 860k lines: metrics in `backend/models/metrics.json` are from that run, nowhere else.

## Known gaps / next steps

- No payer-specific signal (CERT is Medicare-only); payer payment-speed table is illustrative.
- Reliability above ~0.4 predicted degrades (few samples there); could pool years for the high-risk tail.
- Scrubber should eventually be swapped for a NER-based de-id (e.g. Philter) before touching anything real.
