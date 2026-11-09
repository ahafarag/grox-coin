#!/usr/bin/env bash
# Starts the Grox block explorer. Then open http://localhost:8792 in your browser.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec python3 tools/explorer/grox_explorer.py "$@"
