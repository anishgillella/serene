#!/usr/bin/env bash
# Start Serene local dev services on fixed ports.
# Usage: ./scripts/dev.sh [api|agent|frontend|celery|all]
#
# Ports (see docs/project/PORTS.md):
#   API       8100
#   Frontend  8101
#   Redis     6380

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${SERENE_API_PORT:-8100}"
FRONTEND_PORT="${SERENE_FRONTEND_PORT:-8101}"

cmd="${1:-all}"

start_api() {
  echo "→ API on http://localhost:${API_PORT}"
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT" --reload
}

start_agent() {
  echo "→ LiveKit agent (outbound, no local port)"
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python start_agent.py start
}

start_frontend() {
  echo "→ Frontend on http://localhost:${FRONTEND_PORT}"
  cd "$ROOT/frontend"
  npm run dev
}

start_celery() {
  echo "→ Celery worker + beat (Redis :6380)"
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  celery -A app.celery_app worker --loglevel=info --beat
}

case "$cmd" in
  api)      start_api ;;
  agent)    start_agent ;;
  frontend) start_frontend ;;
  celery)   start_celery ;;
  all)
    echo "Open separate terminals for each service:"
    echo "  ./scripts/dev.sh api"
    echo "  ./scripts/dev.sh agent"
    echo "  ./scripts/dev.sh frontend"
    echo "  ./scripts/dev.sh celery   # optional"
    ;;
  *)
    echo "Usage: ./scripts/dev.sh [api|agent|frontend|celery|all]"
    exit 1
    ;;
esac
