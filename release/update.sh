#!/usr/bin/env bash
# Update Grox to the latest release from GitHub.
#
#   ~/grox/update.sh            update if a newer version exists
#   ~/grox/update.sh --check    only say whether an update exists
#   ~/grox/update.sh --force    reinstall the latest version even if you have it
#
# Downloads the package for your Ubuntu version, checks its SHA256, stops Grox, replaces the program
# files and starts the node again if it was running. Your wallets (*.keys files) and the blockchain
# (~/.grox) are not touched.
set -euo pipefail

REPO="ahafarag/grox-coin"
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
MODE="${1:-}"

say()  { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mError:\033[0m %s\n' "$*"; exit 1; }

command -v curl >/dev/null || fail "curl is missing: sudo apt-get install -y curl"
command -v python3 >/dev/null || fail "python3 is missing: sudo apt-get install -y python3"

CURRENT="$(cat "$DIR/wallet-app/VERSION" 2>/dev/null || echo 0)"
LATEST="$(curl -fsSL -H 'Accept: application/vnd.github+json' "https://api.github.com/repos/$REPO/releases/latest" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("vV"))')" \
  || fail "Could not reach GitHub. Check your internet connection and try again."

newer() {  # is $1 newer than $2 ?
  python3 - "$1" "$2" <<'PY'
import sys
v = lambda s: tuple(int(x) if x.isdigit() else 0 for x in s.split("-")[0].split("."))
sys.exit(0 if v(sys.argv[1]) > v(sys.argv[2]) else 1)
PY
}

echo "Installed: v$CURRENT    Latest on GitHub: v$LATEST"
if ! newer "$LATEST" "$CURRENT" && [ "$MODE" != "--force" ]; then
  echo "You already have the latest version."
  exit 0
fi
[ "$MODE" = "--check" ] && { echo "An update is available: run $DIR/update.sh"; exit 0; }

. /etc/os-release
ASSET="grox-linux-x64-ubuntu${VERSION_ID:-}.tar.gz"
BASE="https://github.com/$REPO/releases/download/v$LATEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say "Downloading Grox v$LATEST ($ASSET)"
if ! curl -fsSL "$BASE/$ASSET" -o "$TMP/$ASSET" || ! curl -fsSL "$BASE/$ASSET.sha256" -o "$TMP/$ASSET.sha256"; then
  say "No ready package for ${PRETTY_NAME:-this system}: using the installer (it can build from source)"
  curl -fsSL "https://raw.githubusercontent.com/$REPO/main/install.sh" -o "$TMP/install.sh"
  GROX_DIR="$DIR" exec bash "$TMP/install.sh"
fi

say "Checking the download is genuine (SHA256)"
( cd "$TMP" && sha256sum -c "$ASSET.sha256" ) || fail "Checksum mismatch: the download is damaged or was changed. Nothing was changed."

NODE_WAS_RUNNING=0
curl -s -o /dev/null -m 3 http://127.0.0.1:19881/get_height && NODE_WAS_RUNNING=1

say "Stopping Grox"
"$DIR/stop.sh" >/dev/null 2>&1 || true
for _ in $(seq 1 60); do  # the node saves the blockchain before it exits
  pgrep -f "$DIR/bin/groxd" >/dev/null || pgrep -x groxd >/dev/null || break
  sleep 1
done

say "Installing v$LATEST into $DIR"
tar -xzf "$TMP/$ASSET" -C "$DIR" --strip-components=1

if [ "$NODE_WAS_RUNNING" = 1 ]; then
  say "Starting the node again"
  mkdir -p "$HOME/.grox"
  "$DIR/bin/groxd" --detach --non-interactive --log-file "$HOME/.grox/grox.log" >/dev/null || true
fi

cat <<EOF

  Grox is now v$LATEST

  Start the wallet:  $DIR/start.sh   ->  http://localhost:8790
  What's new:        https://github.com/$REPO/releases/tag/v$LATEST

EOF
