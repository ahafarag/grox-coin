#!/usr/bin/env bash
# Start Grox: the node (in the background) and the wallet app.
# Then open http://localhost:8790 in your browser.
set -euo pipefail
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

if curl -s -o /dev/null -m 3 http://127.0.0.1:19881/get_height; then
  echo "Grox node is already running."
else
  echo "Starting the Grox node in the background..."
  mkdir -p "$HOME/.grox"
  "$DIR/bin/groxd" --detach --non-interactive --log-file "$HOME/.grox/grox.log" >/dev/null
  for _ in $(seq 1 30); do
    curl -s -o /dev/null -m 2 http://127.0.0.1:19881/get_height && break
    sleep 1
  done
fi

URL=http://localhost:8790
echo
echo "  Grox Wallet: $URL"
echo "  (keep this window open; press Ctrl+C to close the wallet)"
echo
# open the browser when we can (WSL -> Windows browser, desktop Linux -> xdg-open)
( sleep 2
  if grep -qi microsoft /proc/version 2>/dev/null && command -v cmd.exe >/dev/null; then
    cmd.exe /c start "$URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi ) &

exec python3 "$DIR/wallet-app/grox_app.py" --bin-dir "$DIR/bin" "$@"
