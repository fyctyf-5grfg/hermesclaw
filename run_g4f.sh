#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8080"
PROMPT="${1:-Reply with exactly: OK}"
MODEL="$(curl -fsSL https://raw.githubusercontent.com/maruf009sultan/g4f-working/refs/heads/main/working/working_results.txt | awk -F'|' 'NF>=3 {print $2}' | head -n 1)"

[ -n "$MODEL" ] || { echo "No working model found" >&2; exit 1; }

python -m pip install -q g4f
curl -fsS "$BASE/v1/models" >/dev/null 2>&1 || {
  python -m g4f --port 8080 >/tmp/g4f.log 2>&1 &
  for i in $(seq 1 60); do
    curl -fsS "$BASE/v1/models" >/dev/null 2>&1 && break
    sleep 1
  done
}

curl -fsS -X POST "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}],\"temperature\":0,\"max_tokens\":16}" \
  | python -c 'import sys,json; obj=json.load(sys.stdin); print(obj["choices"][0]["message"]["content"])'
