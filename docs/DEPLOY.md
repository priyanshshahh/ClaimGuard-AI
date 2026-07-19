# Deploying ClaimGuard-AI

## Frontend (Vercel)

1. Import the `frontend/` directory as a Next.js project.
2. Set env:
   - `NEXT_PUBLIC_API_URL` — backend URL (e.g. `https://api.example.com`)
   - `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` — for login/signup
   - `NEXT_PUBLIC_DEMO_MODE=true` only if you want seed-demo / simulated EHR tools
3. Add your Vercel preview/production origin to backend `CORS_ORIGINS` (comma-separated).
4. Deploy; leave `CORS_ORIGIN_REGEX` empty unless you intentionally need regex matching.

## Backend (container)

```bash
docker compose up --build
```

For production Postgres storage:

```bash
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://...
AUTH_DISABLED=false
API_KEYS=your-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

## Supabase (Postgres + auth)

1. Create a Supabase project and run `supabase/migrations/001_initial.sql`.
2. Create an org row and a `profiles` row linking `auth.users` to the org.
3. Set `DATABASE_URL` to the Supabase connection string (service role for backend).
4. Set `SUPABASE_JWT_SECRET` from Project Settings → API → JWT Secret.
5. Point the frontend at Supabase Auth; `apiFetch` sends `Authorization: Bearer <token>`.

See root `.env.example` for the full variable list.
