# Deploying ClaimGuard-AI

## Frontend — Vercel (live)

Production: https://claimguard-ai-alpha.vercel.app

Project: `pris-projects-ef3397a7/claimguard-ai` (root = `frontend/`)

Required env:
- `NEXT_PUBLIC_API_URL` — Render API URL (e.g. `https://claimguard-api.onrender.com`)
- `NEXT_PUBLIC_DEMO_MODE=true` — enable demo seed tools

```bash
cd frontend
vercel --prod --scope pris-projects-ef3397a7
```

## Backend — Render (free Docker web service)

**Do not use Fly.io.** Use Render free tier + `render.yaml` / `backend/Dockerfile`.

### One-click Blueprint

1. Open: https://render.com/deploy?repo=https://github.com/priyanshshahh/ClaimGuard-AI&branch=real-model
2. Sign in with GitHub, create the `claimguard-api` free web service.
3. Set env:
   - `AUTH_DISABLED=true` (demo)
   - `CORS_ORIGINS=https://claimguard-ai-alpha.vercel.app`
   - `CORS_ORIGIN_REGEX=https://.*\.vercel\.app`
   - Optional: `GROQ_API_KEY`
4. After deploy, copy the `*.onrender.com` URL into Vercel `NEXT_PUBLIC_API_URL`, then redeploy the frontend.

Free tier sleeps after idle (~50s cold start on first request).

### CLI (after `render login`)

```bash
# From repo root — uses render.yaml
render blueprints apply
```

## Local

```bash
docker compose up --build
```

See root `.env.example` for the full variable list.
