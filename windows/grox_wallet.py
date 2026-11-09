#!/usr/bin/env python3
"""Grox Wallet for Windows: wallet + solo mining in one desktop window.

This is what GroxWallet.exe runs. It
  1. starts the Grox node (groxd.exe) hidden in the background,
  2. serves the wallet app (tools/wallet-app) on http://127.0.0.1:8790,
  3. shows it in a normal desktop window (Microsoft Edge WebView2),
  4. when the window closes: saves + closes the wallet, stops mining and the node.

If WebView2 is missing (old Windows 10), the wallet opens in the default browser
and a small "Grox is running" window keeps it alive.

Also runs from source on Windows/Linux for development:
    python windows/grox_wallet.py --bin-dir build/bin
Test/CI flags: --headless (no window, quit with POST /api/quit) and --self-check FILE.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.request
import webbrowser

FROZEN = getattr(sys, "frozen", False)
BASE = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
if not FROZEN:
    sys.path.insert(0, os.path.join(BASE, "..", "tools", "wallet-app"))

import grox_app  # noqa: E402

TITLE = "Grox Wallet"
BG = "#0b0c0f"
QUIT_WHILE_MINING = (
    "Grox is mining. Closing this window stops mining and the Grox node.\n"
    "Your wallet is saved.\n\n"
    "التعدين شغال. لو قفلت الشاشة، التعدين والشبكة هيقفوا.\n"
    "محفظتك محفوظة."
)


def app_data_dir():
    if grox_app.IS_WIN:
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
        return os.path.join(root, "Grox")
    return os.path.join(os.path.expanduser("~"), ".grox-wallet")


def default_bin_dir():
    if FROZEN:
        return os.path.join(BASE, "bin")
    for d in ("bin", os.path.join("..", "build", "bin"), os.path.join("..", "build", "win", "bin")):
        p = os.path.join(BASE, d)
        if os.path.exists(os.path.join(p, "groxd" + grox_app.EXE)):
            return p
    return os.path.join(BASE, "..", "build", "bin")


def icon_path():
    for p in (os.path.join(grox_app.HERE, "grox.ico"), os.path.join(BASE, "grox.ico")):
        if os.path.exists(p):
            return p
    return None


def hold_app_mutex():
    """Named mutex the installer checks (AppMutex) so it never replaces files while Grox runs."""
    if grox_app.IS_WIN:
        try:
            import ctypes
            _MUTEX.append(ctypes.windll.kernel32.CreateMutexW(None, False, "GroxWalletRunning"))
        except Exception:
            pass


_MUTEX = []


def is_grox_wallet(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as r:
            return b"Grox" in r.read(4096)
    except Exception:
        return False


def message_box(text, title=TITLE):
    if grox_app.IS_WIN:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
            return
        except Exception:
            pass
    print(text)


def start_node_in_background():
    def run():
        try:
            grox_app.api_node_start({})
        except Exception as e:  # the page shows "node offline" + a Start button; keep the reason in a log
            log(f"node start failed: {e}")
    threading.Thread(target=run, daemon=True).start()


def log(msg):
    try:
        with open(os.path.join(app_data_dir(), "grox-wallet.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------- windows

def run_webview(url):
    """Desktop window with Edge WebView2. Returns False if WebView2 can't be used."""
    try:
        import webview
        if grox_app.IS_WIN:
            from webview.platforms import winforms
            if getattr(winforms, "renderer", "") != "edgechromium":
                log("WebView2 runtime not found, using the browser instead")
                return False
    except Exception as e:
        log(f"webview unavailable: {e!r}")
        return False

    win = webview.create_window(TITLE, url, width=1200, height=860, min_size=(420, 600),
                                background_color=BG, text_select=True)

    def on_closing():
        # ask only when closing would interrupt mining
        win.confirm_close = grox_app.mining_active()

    win.events.closing += on_closing
    watch_quit(win.destroy)
    storage = os.path.join(app_data_dir(), "webview")
    os.makedirs(storage, exist_ok=True)
    webview.start(gui="edgechromium" if grox_app.IS_WIN else None, private_mode=False, storage_path=storage,
                  localization={"global.quitConfirmation": QUIT_WHILE_MINING}, icon=icon_path())
    return True


def run_fallback(url):
    """No WebView2: open the default browser, keep a small control window."""
    webbrowser.open(url)
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        message_box(f"Grox Wallet is running at {url}\n\nPress OK to close Grox (mining and the node stop).")
        return
    root = tk.Tk()
    root.title(TITLE)
    root.configure(bg=BG)
    root.resizable(False, False)
    ico = icon_path()
    if ico and grox_app.IS_WIN:
        try:
            root.iconbitmap(ico)
        except Exception:
            pass
    tk.Label(root, text="Grox Wallet is running", fg="#f2b544", bg=BG, font=("Segoe UI", 14, "bold")).pack(padx=28, pady=(22, 4))
    tk.Label(root, text=f"It opened in your browser: {url}\nClose this window to stop Grox.\n\n"
                        "المحفظة مفتوحة في المتصفح. اقفل الشاشة دي عشان توقف Grox.",
             fg="#ece9e2", bg=BG, font=("Segoe UI", 10), justify="center").pack(padx=28)
    row = tk.Frame(root, bg=BG)
    row.pack(pady=18)
    tk.Button(row, text="Open wallet", width=14, command=lambda: webbrowser.open(url)).pack(side="left", padx=6)

    def close():
        if grox_app.mining_active() and not messagebox.askokcancel(TITLE, QUIT_WHILE_MINING):
            return
        root.destroy()
    tk.Button(row, text="Close Grox", width=14, command=close).pack(side="left", padx=6)
    root.protocol("WM_DELETE_WINDOW", close)
    watch_quit(lambda: root.after(0, root.destroy))
    root.mainloop()


def watch_quit(close_window):
    """POST /api/quit closes the window too."""
    def run():
        grox_app.QUIT.wait()
        try:
            close_window()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- checks

def self_check(path):
    """Writes what the packaged app can find to a JSON file (used by CI on GroxWallet.exe)."""
    out = {"frozen": FROZEN, "base": BASE, "html": os.path.exists(os.path.join(grox_app.HERE, "index.html")),
           "icon": bool(icon_path())}
    bin_dir = default_bin_dir()
    out["bins"] = {n: os.path.exists(os.path.join(bin_dir, n + grox_app.EXE))
                   for n in ("groxd", "grox-wallet-rpc", "grox-wallet-cli")}
    wallet_dir = os.path.abspath(os.path.expanduser(grox_app.default_wallet_dir()))
    out["wallet_dir"] = wallet_dir
    try:  # can the app create its wallet folder and write a file there?
        os.makedirs(wallet_dir, exist_ok=True)
        probe = os.path.join(wallet_dir, ".grox-write-test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        out["wallet_dir_writable"] = True
    except Exception as e:
        out["wallet_dir_writable"] = repr(e)
    try:
        import webview  # noqa: F401
        out["webview"] = True
        if grox_app.IS_WIN:
            from webview.platforms import winforms
            out["renderer"] = getattr(winforms, "renderer", None)
    except Exception as e:
        out["webview"] = repr(e)
    try:
        import tkinter  # noqa: F401
        out["tk"] = True
    except Exception as e:
        out["tk"] = repr(e)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


# ---------------------------------------------------------------- main

def main():
    ap = grox_app.build_parser()
    ap.description = "Grox Wallet (desktop)"
    ap.set_defaults(bin_dir=default_bin_dir(), log_dir=os.path.join(app_data_dir(), "logs"))
    ap.add_argument("--headless", action="store_true", help="no window; quit with POST /api/quit")
    ap.add_argument("--no-node", action="store_true", help="don't start groxd automatically")
    ap.add_argument("--self-check", metavar="FILE", help=argparse.SUPPRESS)
    args = ap.parse_args()
    args.manage_node = True
    os.makedirs(app_data_dir(), exist_ok=True)

    if args.self_check:
        return self_check(args.self_check)

    url = f"http://127.0.0.1:{args.port}/"
    try:
        grox_app.configure(args)
    except OSError as e:
        message_box(f"Grox Wallet can't use the folder {e.filename or args.wallet_dir}:\n{e.strerror or e}\n\n"
                    "If Windows Security blocked it (ransomware protection), allow GroxWallet.exe there, "
                    "or start Grox Wallet with --wallet-dir <another folder>.")
        sys.exit(1)
    try:
        srv = grox_app.make_server(args.port)
    except OSError:
        if is_grox_wallet(args.port):  # already open: show it again instead of failing
            if not args.headless:
                webbrowser.open(url)
            return
        message_box(f"Port {args.port} is used by another program, so Grox Wallet can't start.\n"
                    f"Close that program, or start Grox Wallet with --port 8791.")
        sys.exit(1)

    hold_app_mutex()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log(f"started, wallets in {grox_app.CFG.wallet_dir}")
    if not args.no_node:
        start_node_in_background()
    try:
        if args.headless:
            print(f"Grox Wallet (headless) on {url}  - POST /api/quit or Ctrl+C to stop")
            while not grox_app.QUIT.wait(0.5):
                pass
        elif not run_webview(url):
            run_fallback(url)
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()
        grox_app.shutdown()
        log("closed")


if __name__ == "__main__":
    main()
