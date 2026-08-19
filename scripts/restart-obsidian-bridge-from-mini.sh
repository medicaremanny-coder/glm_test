#!/usr/bin/env bash
# Restart Obsidian Grok Bot ngrok bridge on the iMac from Mac Mini (or any Mac).
# Bridge host: manny-imac.local (Tailscale 100.64.86.43)
# Tunnel: jockey-prevalent-recluse.ngrok-free.dev
set -euo pipefail

IMAC_HOSTS=(manny-imac.local 100.64.86.43)
DOMAIN="jockey-prevalent-recluse.ngrok-free.dev"
CANDIDATE_PORTS=(3456 27123 3000 27124)

echo "=== Obsidian Grok Bot bridge restart (via iMac) ==="

IMAC=""
for host in "${IMAC_HOSTS[@]}"; do
  if ping -c 1 -t 2 "$host" >/dev/null 2>&1; then
    IMAC="$host"
    echo "Reachable iMac: $host"
    break
  fi
done

if [[ -z "$IMAC" ]]; then
  echo "Cannot reach iMac at: ${IMAC_HOSTS[*]}"
  echo "Ensure Tailscale is connected on both Macs, then retry."
  exit 1
fi

REMOTE_SCRIPT=$(cat <<'EOF'
set -euo pipefail
DOMAIN="jockey-prevalent-recluse.ngrok-free.dev"
LOG="/tmp/ngrok-obsidian.log"
PORTS=(3456 27123 3000 27124)

echo "=== iMac: $(hostname) ==="
ps aux | grep -E '[n]grok|[o]bsidian-mcp|[o]bsidian.*mcp' || true

PORT=""
for p in "${PORTS[@]}"; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    PORT="$p"
    echo "Listener on port $p"
    lsof -nP -iTCP:"$p" -sTCP:LISTEN | head -3
    break
  fi
done

if [[ -z "$PORT" ]]; then
  echo "No Obsidian MCP listener on iMac. Open Obsidian + Local REST API plugin first."
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not on PATH. Try: /opt/homebrew/bin/ngrok or /usr/local/bin/ngrok"
  exit 1
fi

killall ngrok 2>/dev/null || true
sleep 1
nohup ngrok http --domain="$DOMAIN" "$PORT" >"$LOG" 2>&1 &
sleep 4
curl -fsSI "https://${DOMAIN}" | head -5 || { tail -20 "$LOG"; exit 1; }
echo "Tunnel up: https://${DOMAIN}"
EOF
)

echo
echo "=== SSH to iMac and restart ngrok ==="
ssh -o ConnectTimeout=10 -o BatchMode=yes "$IMAC" "bash -s" <<<"$REMOTE_SCRIPT"

echo
echo "=== Verify from this machine ==="
curl -fsSI "https://${DOMAIN}" | head -5
