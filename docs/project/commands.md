# Serene - Run Commands

This file contains all the commands to run the backend, frontend, and agent. Open 3 separate terminal windows and run one command in each.

## Terminal 1: Backend API

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

**Access:**
- API: http://localhost:8100
- API Docs: http://localhost:8100/docs

## Terminal 2: Voice Agent (Luna)

```bash
cd backend
source venv/bin/activate
python start_agent.py start
```

This starts the LiveKit voice agent for real-time mediation.

## Terminal 3: Frontend

```bash
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:8101

## Additional Frontend Commands

Build for production:
```bash
npm run build
```

Preview production build locally:
```bash
npm run preview
```

Run linter:
```bash
npm run lint
```

## Backend Setup (First time only)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Frontend Setup (First time only)

```bash
cd frontend
npm install
```

## Quick Reference

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8100 | http://localhost:8100 |
| API Docs | 8100 | http://localhost:8100/docs |
| Frontend | 8101 | http://localhost:8101 |
| Redis | 6380 | redis://localhost:6380 |
| Voice Agent | — | Background (no inbound port) |

See [`PORTS.md`](PORTS.md) for the full port registry.
