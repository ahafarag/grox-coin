#!/usr/bin/env python3
"""End-to-end test of the Grox Wallet app on a private regtest chain.

Starts the app headless, then through the same HTTP API the page uses:
create a wallet -> solo-mine -> see the rewards -> send GROX -> quit.

    python windows/smoke_test.py -- GroxWallet.exe
    python windows/smoke_test.py -- python windows/grox_wallet.py --bin-dir build/bin

Everything after "--" is the command that starts the app; the test adds
--headless --regtest --port/--wallet-dir/--data-dir/--log-dir itself.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PORT = 18790
URL = f"http://127.0.0.1:{PORT}"


def call(path, body=None, timeout=300):
    req = urllib.request.Request(URL + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Grox": "1", "X-Lang": "en", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")


def wait(what, fn, timeout):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            v = fn()
            if v:
                return v
        except Exception as e:
            last = e
        time.sleep(1)
    raise RuntimeError(f"timed out waiting for {what} (last error: {last})")


def step(msg):
    print(f"[smoke] {msg}", flush=True)


def main():
    # the temp folder has an Arabic name; Windows consoles (cp1252) can't print it otherwise
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if "--" not in sys.argv:
        sys.exit(__doc__)
    cmd = sys.argv[sys.argv.index("--") + 1:]
    # a non-English folder name, like C:\Users\<Arabic name>\Documents: the binaries must still work
    tmp = tempfile.mkdtemp(prefix="grox-smoke-محفظة-")
    cmd += ["--headless", "--regtest", "--port", str(PORT), "--wallet-dir", os.path.join(tmp, "wallets"),
            "--data-dir", os.path.join(tmp, "node"), "--log-dir", os.path.join(tmp, "logs")]
    step("starting: " + " ".join(cmd))
    app = subprocess.Popen(cmd)
    ok = False
    try:
        page = wait("wallet page", lambda: urllib.request.urlopen(URL + "/", timeout=5).read(), 60)
        assert b"Grox" in page, "index.html not served"
        assert call("/api/wallets")["wallets"] == []
        call("/api/node/start", {}, timeout=240)  # the app starts it too; this waits until it answers
        step("node up: " + json.dumps(call("/api/state")["node"]))

        w = call("/api/create", {"name": "smoke", "password": "smoke-pass"})
        assert len(w["seed"].split()) == 25 and w["address"].startswith("G"), w
        step(f"wallet created: {w['address'][:12]}...")

        bad = None
        try:
            call("/api/open", {"file": "smoke", "password": "wrong"})
        except RuntimeError as e:
            bad = str(e)
        assert bad and "Wrong password" in bad, bad
        call("/api/open", {"file": "smoke", "password": "smoke-pass"})

        call("/api/mining", {"action": "start", "threads": 1})
        step("mining started")
        target = 140  # coinbase unlocks after 60 blocks; sending needs 16 decoys too

        def mined():
            s = call("/api/state")
            h = s["node"]["height"]
            print(f"  height {h}  mining={s['mining']['active']}  "
                  f"balance={s['wallet'].get('balance')} unlocked={s['wallet'].get('unlocked')}", flush=True)
            return s if h >= target else None
        st = wait(f"{target} blocks", mined, 900)
        call("/api/mining", {"action": "stop"})
        wait("mining to stop", lambda: not call("/api/state")["mining"]["active"], 60)
        st = call("/api/state")
        wl = st["wallet"]
        assert wl["blocks_found"] > 0 and wl["mined_total"] > 0, wl
        assert wl["unlocked"] > 0, wl
        step(f"mined {wl['blocks_found']} blocks, {wl['mined_total']:.4f} GROX, unlocked {wl['unlocked']:.4f}")

        r = call("/api/send", {"address": wl["address"], "amount": "1.5"})
        assert r["txid"] and r["amount"] == 1.5, r
        step(f"sent 1.5 GROX to self, tx {r['txid'][:16]}..., fee {r['fee']}")

        call("/api/lock", {})
        assert call("/api/state")["wallet"] is None
        ok = True
    finally:
        try:
            call("/api/quit", {}, timeout=10)
        except Exception:
            pass
        try:
            app.wait(timeout=150)
        except subprocess.TimeoutExpired:
            app.kill()
            ok = False
            step("app did not quit in time")
        for f in ("logs/grox-wallet-app-rpc.log", "node/grox.log"):
            p = os.path.join(tmp, f)
            if not ok and os.path.exists(p):
                print(f"----- tail of {f}")
                with open(p, encoding="utf-8", errors="replace") as fh:
                    print("".join(fh.readlines()[-40:]))
        down = True
        try:
            urllib.request.urlopen("http://127.0.0.1:19881/get_height", timeout=3)
            down = False
        except Exception:
            pass
        if not down:
            step("groxd is still running after the app quit")
            ok = False
        shutil.rmtree(tmp, ignore_errors=True)
    step("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
