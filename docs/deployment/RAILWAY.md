# Deploy Serene Backend on Railway

Replace Fly.io with Railway for the FastAPI server and LiveKit agent worker.

**Frontend stays on Vercel.** Point `VITE_API_URL` at your Railway API URL.

---

## Architecture

```
Vercel (frontend)  →  Railway Service 1: serene-api   (FastAPI, public)
                   →  Railway Service 2: serene-agent (LiveKit worker, private)
                   →  Supabase (Postgres)
                   →  LiveKit Cloud
```

Two Railway services, same GitHub repo, both with **Root Directory = `backend`**.

| Service | Start command | Public networking |
|---------|---------------|-------------------|
| `serene-api` | `sh start.sh web` | Yes |
| `serene-agent` | `sh start.sh agent` | No |

---

## 1. Create Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select the `serene` repository
3. Railway creates one service — rename it to `serene-api`

---

## 2. Configure the API service (`serene-api`)

**Settings → General:**
- Root Directory: `backend`
- Config file: `railway.toml`

**Settings → Networking:**
- Generate a public domain (e.g. `serene-api-production.up.railway.app`)

**Variables** — add all keys from `.env.example`:

```bash
# Critical: use Supabase Transaction Pooler (port 6543)
DATABASE_URL=postgres://...@...supabase.co:6543/postgres?pgbouncer=true

LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_AGENT_NAME=luna-mediator

OPENROUTER_API_KEY=...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
VOYAGE_API_KEY=...
PINECONE_API_KEY=...
MISTRAL_API_KEY=...

AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=...

MOSS_PROJECT_ID=...        # optional
MOSS_PROJECT_KEY=...       # optional

SECRET_KEY=<random-64-char-string>
ALLOWED_ORIGINS=https://your-app.vercel.app,https://serene-api-production.up.railway.app
ENABLE_SECURITY_MIDDLEWARE=true
```

**Deploy** — Railway builds from `backend/Dockerfile` and runs `sh start.sh web`.

Health check: `GET /api/health/db`

---

## 3. Add the agent worker (`serene-agent`)

1. In the same Railway project: **+ New Service** → **GitHub Repo** → same `serene` repo
2. Rename to `serene-agent`

**Settings → General:**
- Root Directory: `backend`
- Config file: `railway.agent.toml`

**Settings → Networking:**
- **Disable Public Networking** — the agent only makes outbound WebSocket connections to LiveKit

**Variables** — copy the same env vars as `serene-api` (agent needs LiveKit, AI, DB, Moss keys). Railway supports **shared variables** at the project level to avoid duplicating.

**Deploy** — runs `sh start.sh agent` → `python start_agent.py start`

---

## 4. Update Vercel frontend

In Vercel project settings → Environment Variables:

```bash
VITE_API_URL=https://serene-api-production.up.railway.app
VITE_LIVEKIT_URL=wss://your-project.livekit.cloud
```

Redeploy the frontend after changing `VITE_API_URL`.

---

## 5. Verify

```bash
# API health
curl https://serene-api-production.up.railway.app/api/health/db

# Agent logs (Railway dashboard → serene-agent → Logs)
# Should show: "Starting Luna Mediator Agent" + "Waiting for job requests"
```

Test voice: Post-fight page → Talk to Luna → agent should join the LiveKit room.

---

## CLI deploy (optional)

```bash
npm i -g @railway/cli
railway login
cd backend
railway link          # link to serene-api service
railway up            # deploy API
```

For the agent, switch linked service in dashboard or use `railway service` to select `serene-agent` before `railway up`.

---

## Migrating from Fly.io

1. Deploy Railway services (steps above)
2. Update `VITE_API_URL` on Vercel to Railway URL
3. Update `ALLOWED_ORIGINS` with new Railway domain
4. Confirm voice + API work
5. Delete Fly app: `fly apps destroy serene-backend` (only after Railway is verified)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors from Vercel | Add Vercel URL to `ALLOWED_ORIGINS` on Railway |
| Agent never joins room | Check `serene-agent` logs; verify LiveKit keys; ensure worker service is running |
| DB connection errors | Use port **6543** pooler URL, not direct 5432 |
| Build fails on memory | Upgrade Railway plan or trim `requirements.txt` dev deps |
| Health check fails | Confirm `/api/health/db` returns 200; check `DATABASE_URL` |
