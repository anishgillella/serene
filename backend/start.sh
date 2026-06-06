#!/bin/sh
set -e

PORT="${PORT:-8080}"

case "$1" in
  web)
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  agent)
    exec python start_agent.py start
    ;;
  *)
    echo "Usage: start.sh {web|agent}"
    exit 1
    ;;
esac
