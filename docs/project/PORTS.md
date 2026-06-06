# Serene Local Development Ports

Fixed ports so Serene doesn't collide with other projects on your machine.

| Service | Port | URL | Env var |
|---------|------|-----|---------|
| **Backend API** | `8100` | http://localhost:8100 | `SERENE_API_PORT` |
| **Frontend** | `8101` | http://localhost:8101 | `SERENE_FRONTEND_PORT` |
| **Redis** | `6380` | redis://localhost:6380 | `SERENE_REDIS_PORT` |
| **Vite preview** | `8102` | http://localhost:8102 | — |
| **LiveKit agent** | — | (outbound only, no inbound port) | — |
| **Celery worker** | — | (uses Redis, no HTTP port) | — |

## Why these ports?

Common defaults like `3000`, `5173`, `8000`, and `6379` are used by many tools. Serene uses the `81xx` block for HTTP and `6380` for Redis.

## Quick start

```bash
# Terminal 1 — API
cd backend && source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload

# Terminal 2 — LiveKit agent
cd backend && source venv/bin/activate
python start_agent.py start

# Terminal 3 — Frontend
cd frontend && npm run dev

# Terminal 4 (optional) — Celery
cd backend && source venv/bin/activate
celery -A app.celery_app worker --loglevel=info --beat
```

Or use the helper script:

```bash
./scripts/dev.sh
```

## Environment variables

Set in root `.env` (see `.env.example`):

```bash
SERENE_API_PORT=8100
SERENE_FRONTEND_PORT=8101
SERENE_REDIS_PORT=6380

VITE_API_URL=http://localhost:8100
ALLOWED_ORIGINS=http://localhost:8101

REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2
```

## Running Redis locally

```bash
docker run -d --name serene-redis -p 6380:6379 redis:7-alpine
```

Or with Homebrew Redis on a custom port:

```bash
redis-server --port 6380
```
