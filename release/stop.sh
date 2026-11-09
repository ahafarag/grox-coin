#!/usr/bin/env bash
# Stop Grox: the wallet app and the node (mining stops too).
pkill -TERM -f grox_app.py 2>/dev/null && echo "Wallet app closed." || true
pkill -TERM -f grox_explorer.py 2>/dev/null || true
if curl -s -o /dev/null -m 3 -d '{}' http://127.0.0.1:19881/stop_daemon; then
  echo "Grox node is stopping (it saves the blockchain first, give it a few seconds)."
else
  echo "Grox node was not running."
fi
