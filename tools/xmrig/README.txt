XMRig for Grox (rx/grox)
========================

XMRig 6.26.0 with Grox support: algorithm "rx/grox" (RandomX v2 program, Grox salt).
Built by GitHub Actions from https://github.com/ahafarag/grox-coin
(tools/xmrig: the Grox patch applied to the official XMRig v6.26.0 source).
Developer donation is set to 0%.

SOLO MINING (no pool needed)
1. Run a Grox node on this computer: the Grox Wallet app (Windows) or ~/grox/start.sh (Linux).
   Wait until it is synced. In the app, press Stop mining: XMRig takes over.
2. Edit start-grox-mining.cmd (Windows) or start-grox-mining.sh (Linux) and put your Grox address
   (starts with G) after WALLET=
3. Run the start file. Found blocks are paid to your address by the node.

Command line:
  xmrig --daemon -o 127.0.0.1:19881 -a rx/grox --coin GROX -u <your G... address>

Tips
- Best speed needs ~2.5 GB free RAM (fast mode). With less RAM XMRig uses light mode (slower).
- Huge pages help a lot: run XMRig as Administrator once (Windows) or see XMRig docs (Linux).
- Antivirus programs often flag every crypto miner, including XMRig. Download only from the
  official GitHub releases and check the SHA256.

XMRig is free software under the GNU GPL v3 (see LICENSE). https://github.com/xmrig/xmrig
