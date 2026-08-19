#!/usr/bin/env bash
# Restart Obsidian MCP ngrok tunnel on macOS.
# Domain: jockey-prevalent-recluse.ngrok-free.dev
set -euo pipefail

DOMAIN="jockey-prevalent-recluse.ngrok-free.dev"
LOG="/tmp/ngrok-obsidian.log"
CANDIDATE_PORTS=(3456 27123 3000 27124)

echo "=== Obsidian MCP tunnel restart ==="

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Install with: brew install ngrok/ngrok/ngrok"
  exit 1
fi

echo
echo "=== Running processes ==="
ps aux | grep -E '[n]grok|[o]bsidian-mcp|[o]bsidian.*mcp' || true

echo
echo "=== Listening ports ==="
PORT=""
for p in "${CANDIDATE_PORTS[@]}"; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Found listener on port $p"
    PORT="$p"
    lsof -nP -iTCP:"$p" -sTCP:LISTEN | head -5
    break
  fi
done

if [[ -z "$PORT" ]]; then
  echo "No Obsidian MCP listener found on ports: ${CANDIDATE_PORTS[*]}"
  echo "Start obsidian-mcp first, then rerun this script."
  echo
  echo "Common starts:"
  echo "  cd ~/obsidian-mcp && npm start"
  echo "  npx -y obsidian-mcp-server   # if using Local REST API plugin"
  exit 1
fi

echo
echo "=== Restarting ngrok for port $PORT ==="
killall ngrok 2>/dev/null || true
sleep 1
nohup ngrok http --domain="$DOMAIN" "$PORT" >"$LOG" 2>&1 &
sleep 4

echo
echo "=== Tunnel check ==="
if curl -fsSI "https://${DOMAIN}" | head -5; then
  echo
  echo "Tunnel appears online at https://${DOMAIN}"
  echo "MCP SSE endpoint (if applicable): https://${DOMAIN}/sse"
else
  echo "Tunnel still failing. Recent ngrok log:"
  tail -30 "$LOG" || true
  exit 1
fi
