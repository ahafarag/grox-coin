#!/usr/bin/env bash
# Mine Grox through the public P2Pool node pool.groxcoin.com (beta). No Grox node needed.
# Payouts go straight to your address inside each block the pool finds.
# 1. Put your Grox address (starts with G) below.  2. Run: ./start-grox-pool.sh
WALLET="PUT_YOUR_GROX_ADDRESS_HERE"
POOL="pool.groxcoin.com:3333"

cd "$(dirname "$0")"
if [[ "$WALLET" != G* ]]; then
  echo "Edit start-grox-pool.sh and put your Grox address (starts with G) in WALLET."; exit 1
fi
exec ./xmrig -o "$POOL" -a rx/grox -u "$WALLET" "$@"
