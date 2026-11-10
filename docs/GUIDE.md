# Grox user guide

[العربية](GUIDE.ar.md)

Everything you need to mine Grox, from zero. No technical background needed.

> **On Windows?** The easiest way is the **Grox Wallet app**: one installer, no Ubuntu/WSL.
> See [WINDOWS.md](WINDOWS.md). This guide covers Ubuntu, WSL and servers; sections 5–7
> (mining, sending, backups) work the same in the Windows app.

1. [What you need](#1-what-you-need)
2. [Windows: install Ubuntu (WSL)](#2-windows-install-ubuntu-wsl)
3. [Install Grox](#3-install-grox)
4. [Start Grox and create your wallet](#4-start-grox-and-create-your-wallet)
5. [Mining](#5-mining)
6. [Balance, receiving and sending](#6-balance-receiving-and-sending)
7. [Back up and restore your wallet](#7-back-up-and-restore-your-wallet)
8. [Stop, update, uninstall](#8-stop-update-uninstall)
9. [Running on a server (VPS) without a screen](#9-running-on-a-server-vps-without-a-screen)
10. [Block explorer](#10-block-explorer)
11. [Troubleshooting](#11-troubleshooting)
12. [FAQ](#12-faq)

---

## 1. What you need

- A 64-bit computer (Intel or AMD).
- **Windows 10/11** (with WSL, step 2), or **Ubuntu 22.04 / 24.04**.
- 4 GB RAM or more is best. Mining in fast mode uses about 2.3 GB.
- About 2 GB of free disk space.

## 2. Windows: install Ubuntu (WSL)

Skip this if you already use Ubuntu, or if you use the [Windows app](WINDOWS.md) instead
(recommended on Windows).

1. Click **Start**, type `PowerShell`, right-click it and choose **Run as administrator**.
2. Run:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. Restart the computer when asked.
4. Open **Ubuntu** from the Start menu. The first time, it asks you to create a
   username and password. That is your Ubuntu password (you'll need it once in step 3).

Everything below is typed in the **Ubuntu** window.

## 3. Install Grox

Copy this one line into the Ubuntu window and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/ahafarag/grox-coin/main/install.sh | bash
```

- It asks for your Ubuntu password once (to install system libraries).
- It downloads Grox from GitHub and **checks it is genuine** (SHA256) before installing.
- It installs into the folder `~/grox`. Takes about a minute.

## 4. Start Grox and create your wallet

```bash
~/grox/start.sh
```

This starts the Grox node in the background and opens the wallet in your browser at
**http://localhost:8790** (open it yourself if it doesn't open). Keep the Ubuntu window open.

The first time, the node downloads the blockchain. That takes a few minutes; the page
shows **Syncing** until it is done.

**Create your wallet:**

1. Click **Create wallet**.
2. Choose a name (English letters, e.g. `my-wallet`) and a password.
3. You will see **25 words**. **Write them on paper**, in order.
   - These words *are* your wallet. If you lose them, your coins are gone.
   - Anyone who sees them can take your coins. Never photograph them, never send them
     to anyone, not even to the Grox developer.
4. Tick *"I wrote the 25 words…"* and click **Continue**.

You can switch the page between **English and Arabic** with the button at the top.

## 5. Mining

On the dashboard, press the big **START** button.

- **Threads (CPU cores):** use the `−` / `+` buttons. More threads = more chances, but your
  computer gets busier. Using half your cores is a good start.
- The first minute is slow while the miner prepares its memory, then the speed (H/s) goes up.
- **Expected time per block** shows how often you should find a block on average. It's
  luck: sometimes faster, sometimes slower.
- When you find a block, the reward goes straight into your wallet.
- Mined coins are **locked for 60 blocks (~1 hour)**, then you can spend them.

Mining only runs while the Grox node is running. Close it with `~/grox/stop.sh` (step 8).

## 6. Balance, receiving and sending

- **Balance:** shown at the top of the dashboard. "Spendable" is what you can send now.
- **Receive:** copy your address (starts with `G`) and give it to the sender.
  Your address is safe to share.
- **Send:** paste the receiver's address, the amount, click **Send** and confirm.
  The payment appears in the next block (~1 minute). Transfers can't be undone,
  so double-check the address.

**Privacy:** nobody can look up your balance from your address, and amounts are hidden
on the blockchain. Only you see your balance, in your wallet.

## 7. Back up and restore your wallet

Your **25 words** are the real backup. With them you can restore your wallet anywhere.

**Restore** (new computer, or you forgot the password):

1. Install and start Grox (steps 3-4).
2. Click **Restore a wallet from 25 words**.
3. Type the 25 words, a wallet name and a new password.
4. The wallet scans the blockchain for your coins (takes a minute).

Your wallet files are in your home folder (`~/<name>` and `~/<name>.keys`). The `.keys`
file is protected by your password. Still, the 25 words are what matters.

## 8. Stop, update, uninstall

| What | Command |
|---|---|
| Stop wallet + node + mining | `~/grox/stop.sh` |
| Start again | `~/grox/start.sh` |
| Update to the latest version | run the install line from step 3 again (your wallets are kept) |
| Uninstall | `~/grox/stop.sh` then `rm -rf ~/grox ~/.grox` |

Uninstalling does **not** delete your wallet files. Your 25 words still restore everything.

## 9. Running on a server (VPS) without a screen

Install the same way (step 3). Then use the command line:

```bash
# create a wallet (write down the 25 words, type "address", then "exit")
~/grox/bin/grox-wallet-cli --generate-new-wallet ~/my-wallet

# start the node and mine to your address
~/grox/bin/groxd --detach --start-mining <your G... address> --mining-threads 1

# check
~/grox/bin/groxd status
~/grox/bin/groxd mining_status

# change threads, or mine only when the CPU is idle (background mining)
~/grox/bin/groxd stop_mining
~/grox/bin/groxd start_mining <your G... address> <threads> true true

# open the wallet
~/grox/bin/grox-wallet-cli --wallet-file ~/my-wallet
#   balance | address | transfer <address> <amount> | exit
```

Don't use more threads than the server has cores (`nproc`). If the server also runs
websites, prefer background mining.

To use the wallet page from your own computer, forward the port over SSH:
`ssh -L 8790:localhost:8790 root@<server-ip>`, run `~/grox/start.sh` on the server, then
open http://localhost:8790 on your computer.

**Help the network:** open TCP port **19880** in the server's firewall so other nodes can
connect to yours.

## 10. Block explorer

Public explorer, nothing to install: **https://d7vz9sqd109ta.cloudfront.net**

Or run your own copy against your own node:

```bash
~/grox/explorer.sh
```

Then open **http://localhost:8792**: latest blocks, transactions waiting for the next block,
and search by block number or transaction hash.

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| Page shows **Syncing** for a long time, `0 peers` | Check your internet. On a server, make sure outgoing connections are allowed. Wait a few minutes. |
| "Grox Wallet is already running" / port busy | `~/grox/stop.sh`, wait 5 seconds, then `~/grox/start.sh` |
| "This wallet is open in another program" | Close `grox-wallet-cli` (type `exit`), or run `pkill grox-wallet` |
| "Wrong password" | Use your 25 words to restore (step 7) with a new password |
| Very low H/s | Normal during the first minute. On low-RAM computers (<4 GB) the miner runs in a slower mode. On Windows/WSL, give WSL more memory: create `C:\Users\<you>\.wslconfig` with `[wsl2]` and `memory=8GB`, then run `wsl --shutdown`. |
| "Not enough unlocked GROX" | Mined coins unlock after 60 blocks (~1 hour). |
| Antivirus warning | Some antivirus tools flag any crypto miner. Grox is open source and mines only when you press Start. |
| Installer: "Ubuntu 22.04 or 24.04 is needed" | Use one of those versions (on Windows: `wsl --install -d Ubuntu-24.04`). |

Logs: node `~/.grox/grox.log`, wallet `~/grox-wallet-app-rpc.log`.

## 12. FAQ

**Where can I ask for help?** On Discord: https://discord.gg/V5PaU3SSY (#mining-help), or open an issue on GitHub.

**Is Grox worth money?** No. Grox is a hobby coin for mining and fun. It has no monetary
value, is not an investment, and nothing is sold.

**Why only CPUs?** Grox uses RandomX v2, which is designed for normal processors.
Specialised mining hardware doesn't help. Everyone with a computer gets a fair chance.

**What does the developer get?** 5% of all coins once (block 2) and 5% of every block reward.
Both are written in the code, enforced by every node and visible in the explorer.

**Can anyone see my coins?** No. Addresses, amounts and balances are private (Monero
technology). Your IP address is visible to the nodes you connect to, like any
peer-to-peer network.

**I lost my 25 words and my password.** Then the wallet can't be recovered by anyone.
That's why the words go on paper, in a safe place.
