#!/usr/bin/env bash
# Grox installer for Ubuntu 22.04 / 24.04 (also inside WSL on Windows).
#
#   curl -fsSL https://raw.githubusercontent.com/ahafarag/grox-coin/main/install.sh | bash
#
# Downloads the latest release from GitHub, checks its SHA256 checksum,
# installs the libraries it needs and puts everything in ~/grox.
set -euo pipefail

REPO="ahafarag/grox-coin"
DEST="${GROX_DIR:-$HOME/grox}"
BASE="${GROX_RELEASE_BASE:-https://github.com/$REPO/releases/latest/download}"

say()  { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mError:\033[0m %s\n' "$*"; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "Grox runs on Linux. On Windows, install Ubuntu from the Microsoft Store (WSL) and run this inside it."
[ "$(uname -m)" = "x86_64" ] || fail "Only 64-bit Intel/AMD computers (x86_64) are supported for now."
. /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
  ubuntu:24.04|ubuntu:22.04) ;;
  *) fail "Ubuntu 22.04 or 24.04 is needed (found ${PRETTY_NAME:-unknown}). You can still build from source: see README." ;;
esac

ASSET="grox-linux-x64-ubuntu${VERSION_ID}.tar.gz"

say "Installing the libraries Grox needs (asks for your password once)"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl python3 ca-certificates \
  libboost-chrono-dev libboost-date-time-dev libboost-filesystem-dev libboost-locale-dev \
  libboost-program-options-dev libboost-regex-dev libboost-serialization-dev libboost-system-dev \
  libboost-thread-dev libssl-dev libzmq3-dev libunbound-dev libsodium-dev libunwind8-dev \
  liblzma-dev libreadline-dev libexpat1-dev libpgm-dev libhidapi-dev libusb-1.0-0-dev libudev-dev >/dev/null

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
say "Downloading $ASSET"
curl -fL --progress-bar "$BASE/$ASSET" -o "$TMP/$ASSET"
curl -fsSL "$BASE/$ASSET.sha256" -o "$TMP/$ASSET.sha256"

say "Checking the download is genuine (SHA256)"
( cd "$TMP" && sha256sum -c "$ASSET.sha256" ) || fail "Checksum mismatch, the download is damaged or was changed. Nothing was installed."

say "Installing to $DEST"
if [ -d "$DEST" ]; then
  [ -x "$DEST/stop.sh" ] && "$DEST/stop.sh" >/dev/null 2>&1 || true
  sleep 2
fi
mkdir -p "$DEST"
tar -xzf "$TMP/$ASSET" -C "$DEST" --strip-components=1

cat <<EOF

  Grox is installed in $DEST

  Start it:   $DEST/start.sh
  Then open:  http://localhost:8790   (create a wallet, press Start mining)

  Stop it:    $DEST/stop.sh
  Explorer:   $DEST/explorer.sh   ->  http://localhost:8792

  Your wallets are saved in your home folder (*.keys files).
  Write your 25 words on paper. Never share them with anyone.

EOF
