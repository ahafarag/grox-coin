# Grox Wallet for Windows

[العربية ↓](#العربية)

A normal Windows app: install it, open it, create a wallet, press **Start mining**.
No Ubuntu, no WSL, no command line.

## Install

1. Open the [latest release](https://github.com/ahafarag/grox-coin/releases/latest) and download
   **`GroxWallet-Setup-<version>-win-x64.exe`**.
2. Double-click it. It installs for your user only, no administrator password needed.
   - If Windows says **"Windows protected your PC"**: click **More info** → **Run anyway**.
     This appears because Grox is new and not code-signed.
3. Leave **"Launch Grox Wallet"** ticked and press **Finish**.

Prefer no installer? Download **`GroxWallet-<version>-win-x64-portable.zip`**, unzip it anywhere,
and double-click `GroxWallet.exe`.

Needs Windows 10 or 11, 64-bit. Best with 4 GB RAM or more.

**Check the download (optional):** each file has a `.sha256` file next to it. In PowerShell:
```powershell
Get-FileHash .\GroxWallet-Setup-1.0.0-win-x64.exe -Algorithm SHA256
```
The hash must match the one in the `.sha256` file.

## Use

Open **Grox Wallet** from the Start menu or the desktop.

1. **Create wallet**: pick a name and a password. Then **write the 25 words on paper**.
   They are the only way back into your wallet if your computer dies.
2. **Start mining now**: press the button. Use `+` / `−` to choose how many CPU threads mine.
   More threads, more chances to find a block (your computer gets warmer and louder).
3. When you find a block, the reward appears in your wallet. Mined coins unlock after
   **60 blocks** (about 1 hour).
4. **Receive**: copy your address (starts with `G`). **Send**: paste an address and an amount.

The node (the program that talks to the Grox network) starts by itself. The first time it
downloads the blockchain, which takes a few minutes; mining starts once it is in sync.

**Closing the window** saves your wallet and stops mining and the node. If mining is running,
Grox asks first. To keep mining, keep the window open (you can minimize it).

## Where are my files?

| What | Where |
|---|---|
| Wallet files (back these up) | `Documents\Grox` (shortcut: Start menu → **Grox wallet files**) |
| Blockchain | `C:\ProgramData\grox` |
| Logs | `%LOCALAPPDATA%\Grox\logs` and `C:\ProgramData\grox\grox.log` |
| The app | `%LOCALAPPDATA%\Programs\Grox Wallet` |

**Back up**: your 25 words on paper are the real backup. You can also copy the `*.keys` files
from `Documents\Grox` to a USB stick. To restore on a new computer, choose **Restore** in the app
and type the 25 words.

## Update and uninstall

- **Update**: close Grox Wallet, run the new `GroxWallet-Setup-…exe`. Your wallets and the
  blockchain stay.
- **Uninstall**: Windows Settings → Apps → **Grox Wallet** → Uninstall. Your wallet files in
  `Documents\Grox` and the blockchain in `C:\ProgramData\grox` are **kept**. Delete
  `C:\ProgramData\grox` yourself to free the disk space.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Windows protected your PC" | **More info** → **Run anyway**. |
| Windows Firewall asks about `groxd.exe` | **Allow** lets other Grox nodes connect to you (helps the network). **Cancel** is fine too: mining still works. |
| Antivirus deleted or blocked `groxd.exe` | Many antivirus programs flag *every* crypto miner. Grox mines only when you press Start. Restore the file from quarantine and allow it, or reinstall. |
| The wallet opened in my browser, plus a small "Grox is running" window | Your Windows lacks Microsoft Edge WebView2. The wallet works the same in the browser. To get the normal window, install the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) from Microsoft. |
| "Node offline" for a long time | Press **Start node**. If it stops again, open `C:\ProgramData\grox\grox.log` and look at the last lines. |
| "Port 8790 is used by another program" | Something else uses that port. Close it, or start the app with `GroxWallet.exe --port 8791`. |
| Mining shows a low H/s | Normal in the first minute. Computers with less than 4 GB RAM mine in a slower mode. |

## For developers

- App: [`windows/grox_wallet.py`](../windows/grox_wallet.py) wraps the wallet app
  ([`tools/wallet-app`](../tools/wallet-app)) in a desktop window (Edge WebView2 via pywebview).
- Binaries: `groxd.exe`, `grox-wallet-rpc.exe`, `grox-wallet-cli.exe` are cross-compiled on Ubuntu
  with the pinned libraries in `contrib/depends`
  (see [`.github/workflows/windows.yml`](../.github/workflows/windows.yml)).
- Packaging: [`windows/build.ps1`](../windows/build.ps1) (PyInstaller + Inno Setup).
- Test: [`windows/smoke_test.py`](../windows/smoke_test.py) solo-mines a private regtest chain
  through the app. CI runs it on Windows against the packaged `GroxWallet.exe`.

Run from source on Windows (after building or downloading the `.exe` binaries):
```powershell
pip install pywebview
python windows\grox_wallet.py --bin-dir <folder with groxd.exe>
```

---

<div dir="rtl">

## العربية

## Grox Wallet لويندوز

برنامج ويندوز عادي: تثبّته، تفتحه، تعمل محفظة، وتدوس **ابدأ التعدين**.
من غير Ubuntu ولا WSL ولا أوامر.

### التثبيت

1. افتح [آخر إصدار](https://github.com/ahafarag/grox-coin/releases/latest) ونزّل
   **`GroxWallet-Setup-<version>-win-x64.exe`**.
2. دوس عليه دبل كليك. بيتثبّت لحسابك إنت بس، ومش محتاج كلمة سر المدير.
   - لو ويندوز قال **"Windows protected your PC"**: دوس **More info** وبعدين **Run anyway**.
     ده بيظهر عشان Grox برنامج جديد ومش موقّع.
3. سيب **"Launch Grox Wallet"** متعلّم عليها ودوس **Finish**.

مش عايز تثبيت؟ نزّل **`GroxWallet-<version>-win-x64-portable.zip`**، فكّه في أي مكان، ودوس على `GroxWallet.exe`.

محتاج ويندوز 10 أو 11 (64-bit)، ويفضّل 4 جيجا رام أو أكتر.

### الاستخدام

افتح **Grox Wallet** من قايمة Start أو من سطح المكتب.

1. **إنشاء محفظة**: اختار اسم وكلمة سر، و**اكتب الـ25 كلمة على ورقة**. هي الطريقة الوحيدة ترجع بيها لمحفظتك لو الجهاز باظ.
2. **ابدأ التعدين الآن**: دوس الزرار، واختار عدد الأنوية بـ `+` و `−`. كل ما تزوّد، فرصتك تزيد (والجهاز هيسخن ويعلى صوته).
3. لما تلاقي بلوك، المكافأة بتنزل في محفظتك، وبتتفتح بعد **60 بلوك** (حوالي ساعة).
4. **الاستلام**: انسخ عنوانك (بيبدأ بـ `G`). **الإرسال**: حط العنوان والمبلغ.

الشبكة (groxd) بتشتغل لوحدها. أول مرة بتنزّل البلوكتشين في كام دقيقة، والتعدين بيبدأ بعد ما تخلص.

**لو قفلت الشاشة**، المحفظة بتتحفظ والتعدين والشبكة بيقفوا، ولو التعدين شغال البرنامج هيسألك الأول. عشان تفضل تعدّن، سيب الشاشة مفتوحة (ممكن تصغّرها).

### ملفاتي فين؟

| إيه | فين |
|---|---|
| ملفات المحفظة (خد منها نسخة) | `Documents\Grox` (من قايمة Start: **Grox wallet files**) |
| البلوكتشين | `C:\ProgramData\grox` |
| السجلات | `%LOCALAPPDATA%\Grox\logs` و `C:\ProgramData\grox\grox.log` |

النسخة الاحتياطية الحقيقية هي **الـ25 كلمة على ورقة**. وممكن كمان تنسخ ملفات `*.keys` من `Documents\Grox` على فلاشة. عشان ترجّع المحفظة على جهاز جديد، اختار **استرجاع** واكتب الـ25 كلمة.

### التحديث والحذف

- **التحديث**: اقفل Grox Wallet وشغّل ملف التثبيت الجديد. المحافظ والبلوكتشين بيفضلوا زي ما هم.
- **الحذف**: الإعدادات ← Apps ← **Grox Wallet** ← Uninstall. ملفات المحفظة في `Documents\Grox` والبلوكتشين في `C:\ProgramData\grox` **مش بيتمسحوا**. امسح `C:\ProgramData\grox` بنفسك لو عايز المساحة.

### حل المشاكل

- **Windows protected your PC**: دوس **More info** ثم **Run anyway**.
- **الجدار الناري بيسأل عن `groxd.exe`**: **Allow** بيخلي أجهزة Grox التانية تتصل بيك (بيساعد الشبكة)، و**Cancel** برضه ماشي والتعدين هيشتغل.
- **برنامج الحماية مسح `groxd.exe`**: برامج كتير بتعترض على أي برنامج تعدين. Grox مبيعدّنش غير لما تدوس ابدأ. رجّع الملف من الحجر واسمح بيه، أو ثبّت تاني.
- **المحفظة فتحت في المتصفح ومعاها شاشة صغيرة "Grox is running"**: جهازك ناقصه Microsoft Edge WebView2. المحفظة شغالة عادي في المتصفح، ولو عايز الشاشة العادية ثبّت [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
- **"الشبكة مقفولة" لفترة طويلة**: دوس **تشغيل الشبكة**. لو وقفت تاني، افتح `C:\ProgramData\grox\grox.log` وبص على آخر السطور.

</div>
