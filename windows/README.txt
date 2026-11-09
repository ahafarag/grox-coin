Grox Wallet for Windows
=======================

Start "Grox Wallet" from the Start menu (or double-click GroxWallet.exe).

1. Create wallet: pick a name and a password, then WRITE THE 25 WORDS ON PAPER.
2. Start mining: press the button. More CPU threads = more chances to find a block.
3. Rewards show up in your wallet and unlock after 60 blocks (about 1 hour).

Closing the window saves your wallet and stops mining and the Grox node.

Where things are
  Wallet files ........ Documents\Grox            (back up the *.keys files + your 25 words)
  Blockchain .......... C:\ProgramData\grox
  Logs ................ %LOCALAPPDATA%\Grox\logs  and  C:\ProgramData\grox\grox.log

First start
  - Windows SmartScreen may say "Windows protected your PC" because the app is new
    and not code-signed: press "More info" -> "Run anyway".
  - Windows Firewall may ask about groxd.exe: "Allow" lets other Grox nodes connect
    to you (helps the network). "Cancel" is fine too, mining still works.
  - Some antivirus programs flag every crypto miner. Grox only mines when you press Start.
    If groxd.exe was quarantined, restore it and allow it in your antivirus.

Command line (optional)
  bin\groxd.exe              the node
  bin\grox-wallet-cli.exe    text wallet
  bin\grox-wallet-rpc.exe    wallet service used by the app

Your 25 words ARE your wallet. Never photograph, paste or send them to anyone.
Grox is a hobby coin: no monetary value, not an investment.

Source code and help: https://github.com/ahafarag/grox-coin
