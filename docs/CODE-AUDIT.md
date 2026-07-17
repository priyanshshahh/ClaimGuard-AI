# Code Audit

Internal, honest audit of `real-model` as of this commit. Findings only —
nothing here has been fixed. Ranked by value-to-fix (impact if fixed vs.
effort). "Known non-blocker" = already accepted risk for a demo-stage app,
listed for completeness, not urgency.

## Top findings

### 1. Synchronous LLM calls block the event loop (High value / low effort)
`POST /api/analyze-claim` is `async def` but calls `_analyze_and_store` →
`analyze_clinical_notes` directly, with no `await` and no
`run_in_threadpool`. The Groq (`langchain_groq.ChatGroq`) and Nebius
(`openai.OpenAI`) calls inside `agent.py` are plain synchronous HTTP calls.
Under FastAPI/Starlette, a blocking call made this way runs on the event
loop thread itself — one slow or hung LLM provider stalls **every**
concurrent request the worker is serving, not just the caller's. Combined
with finding #8 (no timeouts), a single unresponsive upstream call can wedge
the whole process indefinitely.
Fix: wrap the LLM call in `starlette.concurrency.run_in_threadpool`, or move
to an async HTTP client (`httpx.AsyncClient` / `AsyncOpenAI`) and `await` it.

### 2. Fabricated business metrics shown as fact in the product UI (High value / low effort)
`frontend/app/reports/page.tsx` (~line 301) and `frontend/app/page.tsx`
(~line 171) both display: *"In our pilots, enabling Treasury mode increased
cash collections by 19% in the first 60 days"* / *"+19% Cash Collections
Improvement — Observed in Treasury mode pilots"*. No pilot exists — this is
invented copy left over from the hackathon pitch. It directly contradicts
the entire premise of the `real-model` rebuild (README: "The model is
trained on real data... honest, reproducible evaluation") and is the kind
of claim that gets a resume/interview candidate into real trouble if anyone
asks "which pilot?". `page.tsx`'s "Autonomous Self-Healing... automatically
retrieves missing labs, history, and prior auths from the EHR" is the same
category of claim (see #3).
Fix: delete both stats or replace with the real, measured model numbers
from `metrics.json` (0.7447 ROC-AUC etc.), clearly labeled as offline
evaluation, not production/pilot results.

### 3. "Self-Healing" EHR retrieval is entirely fake, presented as real (High value / low effort)
`frontend/app/studio/page.tsx` `handleSelfHealing()`: on click, it `await`s
a bare `setTimeout(850ms)`, then string-concatenates a hardcoded fake
enrichment sentence (`"[EHR ENRICHED] Patient weight 187 lbs, HbA1c 6.8..."`)
onto the note and re-runs analysis. The button copy says "Retrieving from
EHR..." then "Self-Healing Complete — EHR data retrieved." There is no EHR
integration anywhere in the backend. The code comment even says "Simulated
enrichment" — but the UI never tells the *user* that. Contrast with
`settings/page.tsx`, which is honest about the same feature area ("FHIR R4
endpoint connected (**simulated**)").
Fix: either relabel the button/toasts as a simulation (cheapest), or remove
the feature — it currently reads as a fabricated capability if screen-shared
in an interview or demo to a technical evaluator.

### 4. Unauthenticated mutating endpoints (Known non-blocker / already flagged)
Every POST route in `main.py` — `/api/analyze-claim`, `/api/seed-demo`,
`/api/clear-queue`, `/api/generate-appeal`, `/api/check-policy`,
`/api/fhir/claim` — has no auth dependency. Anyone who can reach the API can
wipe the queue (`clear-queue`) or flood it with garbage claims. Fine for a
single-user local/demo deployment; would need at minimum an API-key
dependency before any multi-tenant or public deployment.

### 5. CORS regex + `allow_credentials=True` (Known non-blocker / already flagged)
`main.py` sets `allow_origin_regex=r"https://.*\.vercel\.app"` together with
`allow_credentials=True`. Any origin matching `*.vercel.app` — including
other developers' unrelated Vercel projects, not just this app's preview
deployments — is a valid credentialed-request origin. `test_cors.py`
correctly checks the *lookalike-domain* case (`foo.vercel.app.evil.com`
rejected) but doesn't and can't check the *legitimate-other-vercel-app*
case, because by design any `*.vercel.app` origin passes. Acceptable for a
demo with no cookies/session auth in play today; would need a tighter regex
(this project's own preview slug prefix) or drop `allow_credentials` before
introducing cookie-based auth.

### 6. No LLM SDK timeouts (Known non-blocker / already flagged)
Neither `ChatGroq(...)` nor `OpenAI(base_url=NEBIUS_BASE_URL, ...)` in
`agent.py` is constructed with a timeout. Combined with finding #1, a hung
provider connection has no time bound at all. Cheapest partial fix: pass
`timeout=` to both clients even without solving #1.

### 7. Frontend silently substitutes fake data on network failure (Medium value / low effort)
`queue/page.tsx` and `reports/page.tsx` both catch fetch errors and fall
back to two hardcoded claim objects (`CLM-ONC-3914`, `CLM-SPINE-5529`) with
made-up numbers, shown in the exact same table/chart UI as live data, with
only a toast (`"Failed to load queue"`) as the tell — which disappears after
a few seconds while the fake rows stay on screen indefinitely. A user who
misses the toast cannot tell they're looking at fallback data.
Fix: render a persistent "offline / demo fallback" banner alongside the
fallback rows, or just show an empty state instead of fabricated numbers.

### 8. "Resolve & Protect" doesn't persist anything server-side (Medium value / low effort)
`queue/page.tsx` `handleAccept()` shows a success toast and removes the
claim from local React state only — no API call. Reloading the page or
refetching the queue brings the "resolved" claim right back. Either wire it
to a real backend mutation (there's no `/api/resolve-claim` endpoint to call
today) or relabel the button so it doesn't imply a persisted action.

### 9. Clinical-analysis / appeal-letter / policy-check logic is triplicated per provider (Medium value / medium effort)
`agent.py` implements the same pattern three separate times — once for
`analyze_clinical_notes`, once for `generate_appeal_letter`, once for
`check_payer_policy` — each with: try Nebius via a hand-rolled
`OpenAI(base_url=..., response_format={"type":"json_object"})` call +
`model_cls.model_validate(_extract_json(...))`, except-fallback to a
LangChain `ChatGroq | JsonOutputParser` chain, except-fallback to a
hardcoded dict literal. That's 2 provider paths × 3 tasks = 6 near-identical
call sites plus 3 hand-written fallback payloads. A single
`_call_llm(system, user, schema, fallback) -> dict` helper (provider
selection once, `_extract_json` + validate once) would cut this file by
roughly a third and remove the risk of the three copies drifting (they
already differ slightly — e.g. only `_parse_clinical_strict` builds the
Nebius system prompt with an embedded `model_json_schema()`, the appeal/
policy Nebius calls don't).

### 10. Two `.env.example` files with overlapping, drifting content (Low value / low effort)
Root `.env.example` documents backend + training + frontend vars in one
file; `backend/.env.example` separately documents a subset (`GROQ_API_KEY`,
`NEBIUS_API_KEY`, `NEBIUS_BASE_URL`, `NEBIUS_MODEL`) with placeholder-style
values (`your_groq_api_key_here`) instead of the root file's blank-value
style, and it's missing `CORS_ORIGINS`/`CORS_ORIGIN_REGEX`/`DUCKDB_PATH`
entirely. Note: contrary to a common assumption about this file, the root
file's frontend section is actually correct — it lists only
`NEXT_PUBLIC_API_URL`, and Next.js only ever exposes `NEXT_PUBLIC_`-prefixed
vars to client code, so even if someone copied the *entire* root file into
`frontend/.env.local` nothing would leak; the non-prefixed keys would just
be inert. The real issue is just the duplicate/inconsistent file, not a
leak. Fix: delete `backend/.env.example`, keep the root file as the single
source (per its own header comments, that's clearly the intent already).

## Additional / minor findings (not ranked)

- **`backend/duckdb_store.query_priority_queue` is dead in production**: it
  fully re-implements the same ordering `main.py` needs (`ORDER BY
  expected_loss_usd/cash_flow_urgency DESC`) as a SQL query, is exercised by
  `test_store.py`, but `main.py`'s `/api/priority-queue` never calls it —
  the API always goes through `list_claims()` +
  `optimizer.prioritize_claims()` in Python instead. Two implementations of
  "order the queue" exist; one is unused outside its own test.
- **`model.ModelNotAvailableError` and `model.clear_model_cache` are unused**:
  the exception class is raised in `load_model()` but nothing in the app
  ever catches it (it would just 500 the request — though in practice
  `lifespan()` calls `load_model()` at startup, so a missing-artifacts
  failure surfaces as a boot crash, not a runtime exception path).
  `clear_model_cache()` has no caller anywhere, including tests.
- **`frontend/app/components/MetricCard.tsx` is fully unused** — zero
  imports anywhere in the app (verified by grep). `dashboard/page.tsx` and
  `reports/page.tsx` each hand-roll their own near-identical inline KPI card
  markup instead of using it. Dead component + duplicated UI in one finding;
  either delete `MetricCard.tsx` or make the two pages use it.
- **`schemas.ClaimAnalysisResponse.procedure_mismatch`** ("backward compat
  alias") is always set to the exact same value as
  `procedure_mismatch_flag` in `main.py`, and nothing (frontend or tests)
  ever reads the un-suffixed field. It's a pure duplicate column carried
  through the API response and the DuckDB-bound dict.
- **Legacy hackathon artifacts still in the repo root**:
  `ClaimGuard-AI-Pitch-Deck.pptx`, `scripts/generate_pitch_deck.py`,
  `scripts/generate_hackathon_deck.py`, `PROJECT_WRITEUP.md`. These are
  clearly labeled as superseded (`PROJECT_WRITEUP.md` has a status banner
  pointing to the README), and the deck scripts don't reference any
  fabricated model numbers directly (checked — no accuracy/AUC claims
  hardcoded in them), so this is closer to housekeeping than a real problem.
  Worth moving to an `archive/` folder if the repo is being cleaned up
  further, otherwise harmless.
- **`agent.py`'s two JSON-extraction paths handle markdown fences
  differently**: `_extract_json()` (used by the Nebius path) strips
  ```` ```json ```` fences before `json.loads`; the LangChain path relies on
  `JsonOutputParser`'s own extraction. Both currently work against real
  Groq/Nebius output (per `docs/PROJECT-NOTES.md`'s verification notes), but
  it's one more small asymmetry from finding #9 rather than a shared code
  path.
- **`GET /api/priority-queue` and `/api/treasury-priority` hardcode result
  limits** (`prioritized[:15]`, `prioritized[:12]`) with no query parameter
  to change them, and no documented reason for the 15 vs. 12 split.
  Cosmetic, but the asymmetry looks unintentional.

## What's *not* a finding (deliberately correct, worth noting so it isn't
"re-discovered" as a bug later)

- `model_base_probability` vs. `denial_probability` being reported
  separately is intentional and documented (README, `model.py` docstring) —
  this is the right design, not an oversight.
- The PHI scrubber (`deidentify.py`) is explicitly documented as
  best-effort/non-HIPAA-certified in its own module docstring and the
  README. Not re-litigated here.
- The CERT-as-denial-proxy labeling choice is documented in three places
  (README, PROJECT-NOTES, `features.py` docstring) with the same honest
  framing each time — consistent, not a gap.
