# Grox (GROX)

**A private coin you mine with your own computer. No mining rigs, no farms: one CPU, one fair chance.**

**⛏️ Join mining: [say hi and get started in Discussions](https://github.com/ahafarag/grox-coin/discussions/4)**

[العربية ↓](#العربية)

> [!CAUTION]
> **GROX HAS NO OFFICIAL WEBSITE. ANY `grox` DOMAIN (.COM, .ORG, .NET, .IO OR ANY OTHER) IS FAKE.**
> Download Grox **only** from this GitHub repository. Never type your 25 words into any website.
>
> **The only official links:**
> - Code and downloads: **https://github.com/ahafarag/grox-coin** ([releases](https://github.com/ahafarag/grox-coin/releases/latest), each with a SHA256 checksum)
> - Grox page: **https://ahafarag.github.io/grox-coin/** (hosted by GitHub, same account)
> - Block explorer: **https://d7vz9sqd109ta.cloudfront.net**
> - Telegram news: **[@grox_coin](https://t.me/grox_coin)** · Telegram group: **[@grox_community](https://t.me/grox_community)** · bot: **[@grox_coin_bot](https://t.me/grox_coin_bot)**
> - Discord: **https://discord.gg/V5PaU3SSY**
>
> Admins never DM you first and never ask for your 25 words.

| | |
|---|---|
| Ticker | **GROX** |
| Proof of work | RandomX v2 (CPU), Grox variant: stock Monero miners don't work |
| Block time | 1 minute |
| Max supply | **21,000,000 GROX**, hard cap, no tail emission |
| Block reward | ≈ 4.76 GROX at start, slowly decreasing over years |
| Premine | **5%** (1,050,000 GROX) in block 2, to the developer |
| Dev fund | **5%** of every block reward, enforced by every node |
| Privacy | Monero technology: stealth addresses, ring signatures (16), RingCT |
| Addresses | start with `G` |
| P2P port | 19880 |
| Explorer | **https://d7vz9sqd109ta.cloudfront.net** |
| Community | **Discord: https://discord.gg/V5PaU3SSY** · **Telegram: [@grox_community](https://t.me/grox_community)** · news [@grox_coin](https://t.me/grox_coin) |

---

🔎 **Block explorer:** https://d7vz9sqd109ta.cloudfront.net

💬 **Community:** [Discord](https://discord.gg/V5PaU3SSY) · [Telegram group](https://t.me/grox_community) · [Telegram news channel](https://t.me/grox_coin)

> ⬆️ **Network upgrade at block 12,000:** all nodes and miners must run **v1.2.0 or newer** before then. Older versions stop following the network at that block.

📖 **Full step-by-step guide:** [English](docs/GUIDE.md) · [العربية](docs/GUIDE.ar.md)

## Windows: Grox Wallet app (easiest)

Download **`GroxWallet-Setup-<version>-win-x64.exe`** from the
[latest release](https://github.com/ahafarag/grox-coin/releases/latest), run it, open **Grox Wallet**.
Create a wallet, press **Start mining**. Wallet, node and solo mining in one window, no WSL needed.
Details: [docs/WINDOWS.md](docs/WINDOWS.md).

## Install (Ubuntu 22.04 / 24.04, or WSL on Windows)

```bash
curl -fsSL https://raw.githubusercontent.com/ahafarag/grox-coin/main/install.sh | bash
```

The installer downloads the latest release, **checks its SHA256 checksum**, installs the
libraries Grox needs and puts everything in `~/grox`. The release files are built by
GitHub Actions from this repository's code, in public. See the *Actions* tab.

On **Windows** you can also use this route: install *Ubuntu* from the Microsoft Store (that's WSL),
open it and run the command above. The wallet opens in your normal Windows browser.

## Use

```bash
~/grox/start.sh        # starts the node + wallet, then open http://localhost:8790
```

1. **Create wallet**: pick a name and password, then **write the 25 words on paper**.
2. **Start mining**: press the button. More CPU threads, more chances.
3. Rewards appear in your wallet and unlock after 60 blocks (~1 hour).

```bash
~/grox/stop.sh         # stops the wallet and the node
~/grox/explorer.sh     # block explorer at http://localhost:8792
```

Wallets are saved in your home folder (`*.keys`). The node finds the network
automatically through the public seed node.

### Command line (optional)

```bash
~/grox/bin/groxd --start-mining <your G... address> --mining-threads 4
~/grox/bin/grox-wallet-cli --wallet-file ~/<wallet-name>
```

## Safety

- **Your 25 words are your wallet.** Anyone who sees them can take your coins. Never photograph,
  paste or send them, not even to us.
- Everything runs **on your computer**. No server ever sees your keys.
- Balances are private: nobody can look up a balance from an address. Your **IP address** is
  visible to the nodes you connect to, like any peer-to-peer network.
- Some antivirus programs flag *any* crypto miner. Grox mines only when you press Start.

## Premine & dev fund (transparency)

- Block 2 paid the **1,050,000 GROX (5%)** premine to the developer.
- Every block pays **5% of its reward** to the dev fund.
- Both are consensus rules: every node rejects blocks that don't follow them, and anyone can see
  them in the explorer. Code: `src/cryptonote_core/grox_dev_fund_address.cpp`,
  `src/cryptonote_core/cryptonote_tx_utils.cpp`.

**Dedicated dev fund wallet (from block 12,000, v1.2.0).** From block 12,000 the 5% goes to a
dedicated dev fund wallet whose view key is public, so anyone can audit every payment it
receives. A view key can only *see* incoming coins, never spend them.

```
Address:  GDGSHJXsxp8Y3EnLmGMnMcjLs5Qry6H5vibokRCFxKzNbZkggGkNYjd4iHwoMcJkuQKrsVN1Yt7mQY9s6AM5KVaZFLaUw5Y
View key: bb0dd5b0061a6c00f23586a5f11c6b08dbd557369137240449d990c89fe59f02
```

```bash
~/grox/bin/grox-wallet-cli --generate-from-view-key ~/grox-devfund-view
# paste the address and the view key, choose any password, restore height 11990
# then: refresh   and   show_transfers in
```

## Build from source

```bash
git clone https://github.com/ahafarag/grox-coin.git
cd grox-coin
./scripts/setup-ubuntu.sh          # installs build tools + builds into build/bin
```

Then `./scripts/grox-wallet-app.sh` (wallet) or `./scripts/grox-explorer.sh` (explorer).

## Credits & license

Grox is built on the [Monero](https://github.com/monero-project/monero) codebase and
[RandomX](https://github.com/tevador/RandomX). Thanks to their developers.
BSD-3-Clause, see [LICENSE](LICENSE).

---

<div dir="rtl">

## العربية

> **⚠️ Grox ملهاش أي موقع رسمي. أي دومين باسم grox (‎.COM أو ‎.ORG أو ‎.NET أو غيره) مزيّف.**
> نزّل Grox **من GitHub ده بس**، ومتكتبش الـ25 كلمة في أي موقع أبداً.
> اللينكات الرسمية الوحيدة هي اللي فوق في الصندوق الأحمر (GitHub، صفحة GitHub، المستكشف، Telegram، Discord).
> الأدمن عمره ما هيبعتلك رسالة الأول أو يطلب منك الـ25 كلمة.


**عملة رقمية خاصة بتتعدّن بجهازك العادي. مفيش أجهزة تعدين ولا مزارع: كل معالج ليه فرصة.**

| | |
|---|---|
| الرمز | **GROX** |
| التعدين | RandomX v2 بنسخة خاصة بـ Grox (للمعالجات العادية) |
| وقت البلوك | دقيقة |
| أقصى عدد | **21,000,000** وبس |
| مكافأة البلوك | حوالي 4.76 في الأول، وبتقل ببطء على سنين |
| للمطوّر | **5%** مرة واحدة في البلوك 2، و**5%** من كل بلوك، والقاعدتين في الكود وكل الشبكة بتتأكد منهم |
| الخصوصية | تقنية Monero: محدش يقدر يشوف رصيد حد من عنوانه |
| المستكشف | **https://d7vz9sqd109ta.cloudfront.net** |
| المجتمع | **Discord: https://discord.gg/V5PaU3SSY** · **Telegram: [@grox_community](https://t.me/grox_community)** (فيه قسم عربي) |


📖 **الدليل الكامل خطوة بخطوة:** [بالعربي](docs/GUIDE.ar.md)

### ويندوز: برنامج Grox Wallet (الأسهل)

نزّل **`GroxWallet-Setup-<version>-win-x64.exe`** من [آخر إصدار](https://github.com/ahafarag/grox-coin/releases/latest)،
شغّله، وافتح **Grox Wallet**. اعمل محفظة ودوس **ابدأ التعدين**. المحفظة والشبكة والتعدين في شاشة واحدة، من غير WSL.
التفاصيل: [docs/WINDOWS.md](docs/WINDOWS.md#العربية).

### التثبيت (Ubuntu أو WSL على ويندوز)

</div>

```bash
curl -fsSL https://raw.githubusercontent.com/ahafarag/grox-coin/main/install.sh | bash
```

<div dir="rtl">

البرنامج بينزّل آخر نسخة، **ويتأكد إنها سليمة** (SHA256)، وبيحطها في `~/grox`.
النسخ دي بتتبني على GitHub بشكل علني من الكود ده نفسه.

على **ويندوز** ممكن كمان: نزّل *Ubuntu* من Microsoft Store، افتحه، واكتب الأمر اللي فوق.

### التشغيل

</div>

```bash
~/grox/start.sh
```

<div dir="rtl">

بعدها افتح **http://localhost:8790** في المتصفح:

1. **إنشاء محفظة**: اسم وكلمة سر، و**اكتب الـ25 كلمة على ورقة**.
2. **ابدأ التعدين**: كل ما تزوّد الأنوية، فرصتك تزيد.
3. المكافأة بتنزل في محفظتك، وبتتفتح بعد 60 بلوك (حوالي ساعة).

للإيقاف: `~/grox/stop.sh`، وللمستكشف: `~/grox/explorer.sh` ثم **http://localhost:8792**

### الأمان

- **الـ25 كلمة هي محفظتك.** أي حد يشوفهم ياخد فلوسك. متصوّرهمش ومتبعتهمش لحد، ولا حتى لينا.
- كل حاجة بتشتغل **على جهازك إنت**، ومفيش سيرفر بيشوف مفاتيحك.
- بعض برامج مكافحة الفيروسات بتعترض على أي برنامج تعدين. Grox مبيعدّنش غير لما تدوس ابدأ.

</div>
