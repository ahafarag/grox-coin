# Grox v1.2.7

One bundle for everything since v1.2.6. No consensus change: v1.2.6 nodes stay on the network, but please update.

## Updates made easy
- **Grox Wallet app checks for updates** (on start and every 6 hours, from the GitHub releases) and shows a bar when a new version is out. Footer link: *Check for updates*.
- **Windows (installed app): one-click *Update now*.** It downloads the new setup, checks its SHA256, closes the wallet and the node, installs and opens again. Wallets and the blockchain are kept. Portable zip: a button opens the release page.
- **Linux: `~/grox/update.sh`** downloads the package for your Ubuntu version, checks its SHA256, stops Grox, replaces the program files and starts the node again if it was running. `--check` only checks. (First time from an older version: run the install line once more.)

## Easier mining proof (Windows + Linux, app + CLI)
- Grox Wallet app: *Receive → Prove you mined a block* (one click) and *Check someone's proof*.
- `grox-wallet-cli`: `mining_proof [<height>]` and `check_mining_proof <line>`. One line to copy instead of looking up the reward txid and running `get_tx_proof` by hand.
- The check verifies the signature, that the transaction is a block reward, and that it is in the stated block.

## Pool mining from the app
- *Solo / Pool* switch. Pool mode runs Grox XMRig against pool.groxcoin.com:3333 (put the unzipped XMRig folder next to the wallet). XMRig is not bundled in the installer.

## Windows
- Windows Defender: the guide explains the folder exclusions, and the app shows the fix when it blocks `groxd.exe` or `grox-wallet-rpc.exe` ("WinError 225").

## Network
- Checkpoints up to block 12,100, including the block 12,000 fork block.
- Second DNS seed: seeds.groxcoin.com.

## Links
- The wallet app links to groxcoin.com, the web wallet, the explorer and the whitepaper. History shows small payouts with up to 8 decimals.
