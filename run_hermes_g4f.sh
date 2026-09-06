#!/usr/bin/env bash
set -euo pipefail

BASE="${G4F_BASE_URL:-http://127.0.0.1:8080}"
export OPENAI_BASE_URL="${BASE}/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-g4f-local}"

"$(dirname "$0")/run_g4f.sh" --serve >/tmp/g4f.log 2>&1 &
G4F_PID=$!
trap 'kill "$G4F_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do
  if curl -fsS "${BASE}/v1/models" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$G4F_PID" 2>/dev/null; then
    echo "g4f server failed to start" >&2
    cat /tmp/g4f.log >&2 || true
    exit 1
  fi
  sleep 1
done

curl -fsS "${BASE}/v1/models" >/dev/null
exec python3 "$(dirname "$0")/hermes_github_bot.py"