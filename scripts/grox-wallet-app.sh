#!/usr/bin/env bash
# Starts the Grox Wallet app. Then open http://localhost:8790 in your browser (Windows too).
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec python3 tools/wallet-app/grox_app.py "$@"
