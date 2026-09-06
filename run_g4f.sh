#!/usr/bin/env bash
set -euo pipefail

BASE="${G4F_BASE_URL:-http://127.0.0.1:8080}"
PORT="${G4F_PORT:-8080}"

if [[ "${1:-}" == "--serve" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:$PATH"
  uv tool install "g4f[all]"
  exec g4f api --bind "0.0.0.0:$PORT"
fi

PROMPT="${1:-Reply with exactly: OK}"
MODEL="$(curl -fsSL https://raw.githubusercontent.com/maruf009sultan/g4f-working/refs/heads/main/working/working_results.txt | awk -F'|' 'NF>=3 {print $2}' | head -n 1)"

[ -n "$MODEL" ] || { echo "No working model found" >&2; exit 1; }

curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="${HOME}/.local/bin:$PATH"
uv tool install "g4f[all]"
curl -fsS "$BASE/v1/models" >/dev/null 2>&1 || {
  g4f api --bind "0.0.0.0:$PORT" >/tmp/g4f.log 2>&1 &
  READY=0
  for i in $(seq 1 60); do
    if curl -fsS "$BASE/v1/models" >/dev/null 2>&1; then
      READY=1
      break
    fi
    sleep 1
  done
  if [[ "$READY" != 1 ]]; then
    echo "g4f server did not become ready" >&2
    cat /tmp/g4f.log >&2 || true
    exit 1
  fi
}

curl -fsS -X POST "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"temperature\":0,\"max_tokens\":16}" \
  | python -c 'import sys,json; obj=json.load(sys.stdin); print(obj["choices"][0]["message"]["content"])'
