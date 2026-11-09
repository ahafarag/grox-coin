#!/usr/bin/env bash
# Builds Grox (groxd, grox-wallet-cli, grox-wallet-rpc) on Ubuntu 22.04/24.04 or WSL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOBS="${JOBS:-$(nproc)}"

echo "==> Installing build dependencies (needs sudo)"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential cmake pkg-config git ccache \
  libssl-dev libzmq3-dev libunbound-dev libsodium-dev libunwind8-dev \
  liblzma-dev libreadline6-dev libexpat1-dev libpgm-dev qttools5-dev-tools \
  libhidapi-dev libusb-1.0-0-dev libprotobuf-dev protobuf-compiler libudev-dev \
  libboost-chrono-dev libboost-date-time-dev libboost-filesystem-dev \
  libboost-locale-dev libboost-program-options-dev libboost-regex-dev \
  libboost-serialization-dev libboost-system-dev libboost-thread-dev

echo "==> Configuring"
mkdir -p "$ROOT/build"
cd "$ROOT/build"
cmake "$ROOT" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DUSE_DEVICE_TREZOR=OFF \
  -DMANUAL_SUBMODULES=1 -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache

echo "==> Building with $JOBS threads (this takes a while the first time)"
# each compile job can use ~1.5 GB RAM; lower JOBS if the build runs out of memory
make -j"$JOBS" daemon simplewallet wallet_rpc_server

echo
echo "Done. Binaries:"
ls -1 "$ROOT/build/bin/"
