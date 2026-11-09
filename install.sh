#!/usr/bin/env bash
# Grox installer for Ubuntu 22.04 / 24.04 (also inside WSL on Windows).
#
#   curl -fsSL https://raw.githubusercontent.com/ahafarag/grox-coin/main/install.sh | bash
#
# Downloads the latest release from GitHub and checks its SHA256 checksum.
# If there is no ready package for your system, it builds Grox from this
# repository's public source code instead (20-60 minutes, once).
# Everything ends up in ~/grox.
set -euo pipefail

REPO="ahafarag/grox-coin"
DEST="${GROX_DIR:-$HOME/grox}"
BASE="${GROX_RELEASE_BASE:-https://github.com/$REPO/releases/latest/download}"

say()  { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mError:\033[0m %s\n' "$*"; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "Grox runs on Linux. On Windows, install Ubuntu from the Microsoft Store (WSL) and run this inside it."
[ "$(uname -m)" = "x86_64" ] || fail "Only 64-bit Intel/AMD computers (x86_64) are supported for now."
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) fail "Ubuntu (22.04 / 24.04 recommended) or Debian is needed (found ${PRETTY_NAME:-unknown})." ;;
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
PKG=""

say "Looking for a ready package ($ASSET)"
if [ -z "${GROX_FROM_SOURCE:-}" ] && curl -fsL "$BASE/$ASSET" -o "$TMP/$ASSET" 2>/dev/null \
   && curl -fsL "$BASE/$ASSET.sha256" -o "$TMP/$ASSET.sha256" 2>/dev/null; then
  say "Checking the download is genuine (SHA256)"
  ( cd "$TMP" && sha256sum -c "$ASSET.sha256" ) || fail "Checksum mismatch, the download is damaged or was changed. Nothing was installed."
  PKG="$TMP/$ASSET"
else
  say "No ready package, building Grox from source (20-60 minutes, only once)"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git build-essential cmake pkg-config \
    libprotobuf-dev protobuf-compiler qttools5-dev-tools >/dev/null
  SRC="${GROX_SRC:-$HOME/grox-src}"
  if [ -d "$SRC/.git" ]; then
    git -C "$SRC" pull -q --ff-only
  else
    git clone -q --depth 1 "https://github.com/$REPO.git" "$SRC"
  fi
  # each compile job needs ~1.5 GB RAM; don't overload small machines
  MEM_GB=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo)
  JOBS=$(( MEM_GB * 2 / 3 )); [ "$JOBS" -lt 1 ] && JOBS=1
  [ "$JOBS" -gt "$(nproc)" ] && JOBS=$(nproc)
  [ "$MEM_GB" -lt 3 ] && echo "Note: this machine has ${MEM_GB} GB RAM. If the build fails, add swap (2-4 GB) and run again."
  mkdir -p "$SRC/build"
  ( cd "$SRC/build" \
    && cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF -DMANUAL_SUBMODULES=1 >/dev/null \
    && echo "Compiling with $JOBS job(s)... (this is the long part)" \
    && make -j"$JOBS" daemon simplewallet wallet_rpc_server 2>&1 | grep -E --line-buffered "^\[ *[0-9]+%\]" | awk '{ if ($2 != last) { printf "\r  %s", $2; last = $2 } } END { print "" }' ) \
    || fail "Build failed. Check that the machine has enough RAM (add swap) and try again."
  [ -x "$SRC/build/bin/groxd" ] || fail "Build failed (groxd missing). Run it again, or see README to build by hand."
  "$SRC/release/package.sh" "${VERSION_ID:-src}" >/dev/null
  PKG="$SRC/dist/$ASSET"
fi

say "Installing to $DEST"
if [ -d "$DEST" ]; then
  [ -x "$DEST/stop.sh" ] && "$DEST/stop.sh" >/dev/null 2>&1 || true
  sleep 2
fi
mkdir -p "$DEST"
tar -xzf "$PKG" -C "$DEST" --strip-components=1

cat <<EOF

  Grox is installed in $DEST

  Start it:   $DEST/start.sh
  Then open:  http://localhost:8790   (create a wallet, press Start mining)

  Stop it:    $DEST/stop.sh
  Explorer:   $DEST/explorer.sh   ->  http://localhost:8792

  Your wallets are saved in your home folder (*.keys files).
  Write your 25 words on paper. Never share them with anyone.

EOF
