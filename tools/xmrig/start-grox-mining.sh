#!/usr/bin/env bash
# Solo-mine Grox with XMRig. Needs a Grox node (groxd or the Grox Wallet app) running on this computer.
# 1. Put your Grox address (starts with G) below.
# 2. Stop mining inside the Grox Wallet app (XMRig does the mining now).
# 3. Run: ./start-grox-mining.sh
WALLET="PUT_YOUR_GROX_ADDRESS_HERE"
NODE="127.0.0.1:19881"

cd "$(dirname "$0")"
if [[ "$WALLET" != G* ]]; then
  echo "Edit start-grox-mining.sh and put your Grox address (starts with G) in WALLET."; exit 1
fi
exec ./xmrig --daemon -o "$NODE" -a rx/grox --coin GROX -u "$WALLET" "$@"
