#!/usr/bin/env bash
# Package built binaries + apps into dist/grox-linux-x64-ubuntu<ver>.tar.gz (+ .sha256)
#   ./release/package.sh 24.04
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="${1:?ubuntu version, e.g. 24.04}"
BIN="${BIN_DIR:-$ROOT/build/bin}"
NAME="grox-linux-x64-ubuntu$VER"
OUT="$ROOT/dist"
STAGE="$OUT/$NAME"

rm -rf "$STAGE" && mkdir -p "$STAGE/bin"
for f in groxd grox-wallet-cli grox-wallet-rpc; do
  install -m 755 "$BIN/$f" "$STAGE/bin/$f"
  strip "$STAGE/bin/$f" || true
done
mkdir -p "$STAGE/wallet-app" "$STAGE/explorer"
cp "$ROOT/tools/wallet-app/grox_app.py" "$ROOT/tools/wallet-app/index.html" "$ROOT/release/VERSION" "$STAGE/wallet-app/"
cp "$ROOT/tools/explorer/grox_explorer.py" "$ROOT/tools/explorer/index.html" "$STAGE/explorer/"
install -m 755 "$ROOT/release/start.sh" "$ROOT/release/stop.sh" "$ROOT/release/explorer.sh" "$STAGE/"
cp "$ROOT/README.md" "$ROOT/LICENSE" "$STAGE/"

tar -C "$OUT" -czf "$OUT/$NAME.tar.gz" "$NAME"
( cd "$OUT" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256" )
rm -rf "$STAGE"
echo "Built $OUT/$NAME.tar.gz"
cat "$OUT/$NAME.tar.gz.sha256"
