# Serene - Run Commands

This file contains all the commands to run the backend, frontend, and agent. Open 3 separate terminal windows and run one command in each.

## Terminal 1: Backend API

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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
npm run dev -- --port 3000
```

**Access:**
- Frontend: http://localhost:3000

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

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Voice Agent | Background service (accessed via Frontend) |
