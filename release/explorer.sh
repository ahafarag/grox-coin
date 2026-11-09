#!/usr/bin/env bash
# Start the Grox block explorer, then open http://localhost:8792
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
echo "Grox explorer: http://localhost:8792  (Ctrl+C to close)"
exec python3 "$DIR/explorer/grox_explorer.py" "$@"
