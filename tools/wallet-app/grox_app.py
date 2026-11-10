#!/usr/bin/env python3
"""Grox Wallet app - a small local GUI for groxd + grox-wallet-rpc.

Runs a tiny web server on 127.0.0.1 (default port 8790). Open
http://localhost:8790 in your browser (on Windows too, when this runs in WSL).
On Windows it also runs natively: windows/grox_wallet.py wraps it in a desktop
window (GroxWallet.exe).

Only the Python standard library is used.
"""
import argparse
import decimal
import glob
import json
import os
import secrets
import shlex
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ATOMIC = 10 ** 11  # 1 GROX = 10^11 groxatoms
# PyInstaller (GroxWallet.exe) unpacks bundled files (index.html) into sys._MEIPASS
HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
IS_WIN = os.name == "nt"


def _app_version():
    """release/VERSION, shipped next to this file in the packages."""
    for p in (os.path.join(HERE, "VERSION"), os.path.join(HERE, "..", "..", "release", "VERSION")):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    return ""


APP_VERSION = _app_version()
EXE = ".exe" if IS_WIN else ""
CREATE_NO_WINDOW = 0x08000000  # Windows: don't flash a console window for groxd / grox-wallet-rpc


def documents_dir():
    """The user's real Documents folder (follows OneDrive / moved folders on Windows)."""
    if IS_WIN:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:  # CSIDL_PERSONAL
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def default_wallet_dir():
    """Linux: the home folder. Windows: C:\\Users\\<you>\\Grox.

    Not Documents: Windows Security's ransomware protection (Controlled folder
    access) and redirected / OneDrive Documents folders can stop programs from
    writing there, so wallets could not be created. Wallets that v1.1.0 already
    put in Documents\\Grox keep being used from there."""
    if not IS_WIN:
        return "~"
    home = os.path.join(os.path.expanduser("~"), "Grox")
    old = os.path.join(documents_dir(), "Grox")
    if not glob.glob(os.path.join(home, "*.keys")) and glob.glob(os.path.join(old, "*.keys")):
        return old
    return home


def default_node_data_dir(testnet=False):
    """Where groxd keeps the blockchain when no --data-dir is given (see get_default_data_dir)."""
    if IS_WIN:
        base = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "grox")
    else:
        base = os.path.join(os.path.expanduser("~"), ".grox")
    return os.path.join(base, "testnet") if testnet else base


def arg_path(path):
    """A path that is safe to pass on the command line of groxd / grox-wallet-rpc.

    On Windows the Monero code reads its arguments in the ANSI code page, so a
    folder like C:\\Users\\<Arabic name>\\Documents would arrive garbled. For such
    paths use the short 8.3 name (plain ASCII), which Windows keeps for them."""
    if not IS_WIN or path.isascii():
        return path
    try:
        import ctypes
        target = path if os.path.isdir(path) else os.path.dirname(path)
        os.makedirs(target, exist_ok=True)
        buf = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(target, buf, 1024) and buf.value.isascii():
            return buf.value if target == path else os.path.join(buf.value, os.path.basename(path))
    except Exception:
        pass
    return path


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


class Config:
    def __init__(self, args):
        self.testnet = args.testnet
        self.regtest = getattr(args, "regtest", False)
        self.bin_dir = os.path.abspath(os.path.expanduser(args.bin_dir))
        self.wallet_dir = os.path.abspath(os.path.expanduser(args.wallet_dir))
        os.makedirs(self.wallet_dir, exist_ok=True)
        self.log_dir = os.path.abspath(os.path.expanduser(getattr(args, "log_dir", None) or self.wallet_dir))
        os.makedirs(self.log_dir, exist_ok=True)
        self.daemon_port = 29881 if args.testnet else 19881
        self.wallet_rpc_port = 29885 if args.testnet else 19885
        node_args = args.node_args
        self.node_args = list(node_args) if isinstance(node_args, (list, tuple)) else shlex.split(node_args, posix=not IS_WIN)
        data_dir = getattr(args, "data_dir", None)
        if data_dir:
            data_dir = os.path.abspath(os.path.expanduser(data_dir))
            os.makedirs(data_dir, exist_ok=True)
            self.node_args += ["--data-dir", arg_path(data_dir)]
            self.node_log = os.path.join(data_dir, "testnet", "grox.log") if args.testnet else os.path.join(data_dir, "grox.log")
        else:
            self.node_log = os.path.join(default_node_data_dir(args.testnet), "grox.log")
        if self.regtest:
            # private one-computer chain for tests: no peers, every hash finds a block
            self.node_args += ["--regtest", "--offline", "--fixed-difficulty", "1", "--no-igd"]
        # groxd started by this app (Windows desktop app) is stopped again when the app closes
        self.manage_node = getattr(args, "manage_node", False)
        self.daemon = f"http://127.0.0.1:{self.daemon_port}"
        # random credentials so no other local program can use the wallet RPC
        self.rpc_user = "grox"
        self.rpc_pass = secrets.token_hex(16)

    @property
    def wallet_rpc(self):
        return f"http://127.0.0.1:{self.wallet_rpc_port}"


CFG = None
LOCK = threading.Lock()
NODE_LOCK = threading.Lock()
STATE = {"wallet_proc": None, "wallet_file": None, "node_proc": None}
QUIT = threading.Event()  # set by POST /api/quit (used by the desktop app / tests)
_JOB = []


def _kill_with_us(proc):
    """Windows: put a child in a job object that is closed when this app exits,
    so groxd / grox-wallet-rpc never keep running (and mining) invisibly after a crash."""
    if not IS_WIN:
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        if not _JOB:
            class IoCounters(ctypes.Structure):
                _fields_ = [(n, ctypes.c_ulonglong) for n in ("ro", "wo", "oo", "rb", "wb", "ob")]

            class Basic(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class Extended(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IoCounters),
                            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

            job = k32.CreateJobObjectW(None, None)
            info = Extended()
            info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))  # ExtendedLimitInformation
            _JOB.append(job)
        k32.AssignProcessToJobObject(_JOB[0], proc._handle)
    except Exception:
        pass


def _spawn(cmd):
    kw = {"creationflags": CREATE_NO_WINDOW} if IS_WIN else {}
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    _kill_with_us(p)
    return p


class RpcError(Exception):
    pass


def _digest_header(www, method, uri):
    """Build an HTTP Digest (MD5, qop=auth) Authorization header."""
    import hashlib
    import re
    fields = dict(re.findall(r'(\w+)="?([^",]+)"?', www))
    realm, nonce = fields.get("realm", ""), fields.get("nonce", "")
    md5 = lambda x: hashlib.md5(x.encode()).hexdigest()
    ha1 = md5(f"{CFG.rpc_user}:{realm}:{CFG.rpc_pass}")
    ha2 = md5(f"{method}:{uri}")
    cnonce = secrets.token_hex(8)
    nc = "00000001"
    resp = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
    return (f'Digest username="{CFG.rpc_user}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
            f'algorithm=MD5, response="{resp}", qop=auth, nc={nc}, cnonce="{cnonce}"')


def _post(url, payload, auth=False, timeout=30):
    """POST JSON. With auth, does HTTP Digest on one kept-alive connection
    (epee ties the digest nonce to the TCP connection)."""
    import http.client
    u = urllib.request.urlparse(url)
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=timeout)
    try:
        conn.request("POST", u.path, body=data, headers=headers)
        r = conn.getresponse()
        body = r.read()
        if r.status == 401 and auth:
            www = [v for k, v in r.getheaders() if k.lower() == "www-authenticate"]
            www = next((v for v in www if "algorithm=MD5," in v), www[0] if www else "")
            headers["Authorization"] = _digest_header(www, "POST", u.path)
            conn.request("POST", u.path, body=data, headers=headers)
            r = conn.getresponse()
            body = r.read()
        if r.status != 200:
            raise urllib.error.HTTPError(url, r.status, r.reason, r.headers, None)
        return json.loads(body.decode() or "{}")
    except (ConnectionError, OSError) as e:
        if isinstance(e, urllib.error.HTTPError):
            raise
        raise urllib.error.URLError(e)
    finally:
        conn.close()


def daemon_json(method, params=None):
    r = _post(CFG.daemon + "/json_rpc", {"jsonrpc": "2.0", "id": 0, "method": method, "params": params or {}})
    if "error" in r:
        raise RpcError(r["error"].get("message", str(r["error"])))
    return r["result"]


def daemon_other(path, payload=None):
    return _post(CFG.daemon + "/" + path, payload or {})


def wallet(method, params=None, timeout=60):
    r = _post(CFG.wallet_rpc + "/json_rpc", {"jsonrpc": "2.0", "id": 0, "method": method, "params": params or {}},
              auth=True, timeout=timeout)
    if "error" in r:
        raise RpcError(r["error"].get("message", str(r["error"])))
    return r["result"]


def daemon_up():
    try:
        daemon_json("get_info")
        return True
    except Exception:
        return False


def wallet_rpc_up():
    try:
        wallet("get_version", timeout=5)
        return True
    except Exception:
        return False


def start_wallet_rpc():
    if STATE["wallet_proc"] and STATE["wallet_proc"].poll() is None and wallet_rpc_up():
        return
    # an old copy (e.g. left over from a crash) may hold the usual port; use another one
    if not port_free(CFG.wallet_rpc_port):
        CFG.wallet_rpc_port = free_port()
    exe = os.path.join(CFG.bin_dir, "grox-wallet-rpc" + EXE)
    log = os.path.join(CFG.log_dir, "grox-wallet-app-rpc.log")
    cmd = [exe, "--wallet-dir", arg_path(CFG.wallet_dir), "--rpc-bind-ip", "127.0.0.1",
           "--rpc-bind-port", str(CFG.wallet_rpc_port),
           "--rpc-login", f"{CFG.rpc_user}:{CFG.rpc_pass}",
           "--daemon-address", f"127.0.0.1:{CFG.daemon_port}", "--trusted-daemon",
           "--log-file", arg_path(log)]
    if CFG.testnet:
        cmd.append("--testnet")
    if CFG.regtest:  # regtest turns on every fork at height 1, mainnet wallets expect v16 from height 2
        cmd.append("--allow-mismatched-daemon-version")
    if not os.path.exists(exe):
        raise RpcError(f"grox-wallet-rpc{EXE} is missing from {CFG.bin_dir}. Reinstall Grox.")
    STATE["wallet_proc"] = _spawn(cmd)
    for _ in range(120):
        if wallet_rpc_up():
            return
        if STATE["wallet_proc"].poll() is not None:
            hint = ("end grox-wallet-rpc.exe in Task Manager" if IS_WIN else "run: pkill grox-wallet-rpc")
            raise RpcError(f"grox-wallet-rpc could not start. If an old copy is still running, "
                           f"{hint}  (details in {log})")
        time.sleep(0.5)
    raise RpcError("grox-wallet-rpc did not start")


def stop_wallet_rpc():
    if wallet_rpc_up():
        try:
            wallet("stop_wallet", timeout=20)
        except Exception:
            pass
    p = STATE["wallet_proc"]
    if p and p.poll() is None:
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.terminate()
    STATE["wallet_proc"] = None
    STATE["wallet_file"] = None


def to_atomic(amount_str):
    try:
        d = decimal.Decimal(str(amount_str).strip())
    except decimal.InvalidOperation:
        raise RpcError("المبلغ غير صحيح")
    if d <= 0:
        raise RpcError("المبلغ لازم يكون أكبر من صفر")
    atomic = d * ATOMIC
    if atomic != atomic.to_integral_value():
        raise RpcError("أقصى عدد أرقام بعد العلامة العشرية 11")
    return int(atomic)


# ---------------------------------------------------------------- API

def api_wallets(_body):
    files = sorted(glob.glob(os.path.join(CFG.wallet_dir, "*.keys")))
    names = [os.path.basename(f)[:-5] for f in files if not f.endswith(".backup")]
    return {"wallets": names, "dir": CFG.wallet_dir, "open": STATE["wallet_file"]}


def api_open(body):
    name = os.path.basename(body.get("file", ""))
    if not name or not os.path.exists(os.path.join(CFG.wallet_dir, name + ".keys")):
        raise RpcError("المحفظة غير موجودة")
    with LOCK:
        start_wallet_rpc()
        try:
            wallet("close_wallet", timeout=20)
        except Exception:
            pass
        try:
            wallet("open_wallet", {"filename": name, "password": body.get("password", "")}, timeout=120)
        except RpcError as e:
            msg = str(e)
            if "password" in msg.lower():
                raise RpcError("كلمة السر غلط")
            if "opened by another" in msg:
                raise RpcError("المحفظة مفتوحة في برنامج تاني (grox-wallet-cli أو نسخة قديمة من grox-wallet-rpc). اقفله الأول، أو اعمل ريستارت للجهاز.")
            raise
        STATE["wallet_file"] = name
    return {"ok": True}


def _check_new_wallet(body):
    import re
    name = body.get("name", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        raise RpcError("اسم المحفظة: حروف إنجليزي وأرقام و - و _ بس")
    if os.path.exists(os.path.join(CFG.wallet_dir, name + ".keys")):
        raise RpcError("فيه محفظة بنفس الاسم، اختار اسم تاني")
    pw = body.get("password", "")
    if len(pw) < 6:
        raise RpcError("كلمة السر لازم 6 حروف على الأقل")
    return name, pw


def api_create(body):
    name, pw = _check_new_wallet(body)
    with LOCK:
        start_wallet_rpc()
        try:
            wallet("close_wallet", timeout=20)
        except Exception:
            pass
        wallet("create_wallet", {"filename": name, "password": pw, "language": "English"}, timeout=120)
        STATE["wallet_file"] = name
        seed = wallet("query_key", {"key_type": "mnemonic"})["key"]
        addr = wallet("get_address", {"account_index": 0})["address"]
    return {"seed": seed, "address": addr, "name": name}


def api_restore(body):
    name, pw = _check_new_wallet(body)
    seed = " ".join(body.get("seed", "").split()).lower()
    if len(seed.split()) != 25:
        raise RpcError("لازم 25 كلمة بالظبط")
    with LOCK:
        start_wallet_rpc()
        try:
            wallet("close_wallet", timeout=20)
        except Exception:
            pass
        try:
            r = wallet("restore_deterministic_wallet", {"filename": name, "password": pw, "seed": seed,
                                                        "restore_height": 0, "language": "English"}, timeout=300)
        except RpcError as e:
            raise RpcError("الكلمات غير صحيحة، راجعها تاني") if "seed" in str(e).lower() or "electrum" in str(e).lower() else e
        STATE["wallet_file"] = name
    return {"address": r.get("address"), "name": name}


def api_lock(_body):
    with LOCK:
        if wallet_rpc_up():
            try:
                wallet("close_wallet", timeout=30)
            except Exception:
                pass
        STATE["wallet_file"] = None
    return {"ok": True}


def api_state(_body):
    out = {"node": None, "mining": None, "wallet": None, "network": "testnet" if CFG.testnet else "mainnet", "app": {"version": APP_VERSION, "windows": IS_WIN}}
    try:
        info = daemon_json("get_info")
        out["node"] = {
            "height": info["height"],
            "synchronized": info.get("synchronized", False),
            "peers": info.get("outgoing_connections_count", 0) + info.get("incoming_connections_count", 0),
            "difficulty": info.get("difficulty", 0),
            "net_hashrate": round(info.get("difficulty", 0) / max(info.get("target", 60), 1)),
            "version": info.get("version", ""),
        }
        ms = daemon_other("mining_status")
        out["mining"] = {"active": ms.get("active", False), "speed": ms.get("speed", 0),
                         "threads": ms.get("threads_count", 0), "address": ms.get("address", "")}
        try:
            last = daemon_json("get_last_block_header")["block_header"]
            out["node"]["last_block_time"] = last["timestamp"]
            out["node"]["reward"] = last["reward"] / ATOMIC
        except Exception:
            pass
    except Exception:
        pass

    if STATE["wallet_file"] and wallet_rpc_up():
        try:
            try:
                wallet("refresh", timeout=120)
            except Exception:
                pass
            bal = wallet("get_balance")
            addr = wallet("get_address", {"account_index": 0})["address"]
            height = wallet("get_height")["height"]
            tr = wallet("get_transfers", {"in": True, "out": True, "pending": True, "pool": True, "failed": False})
            is_dev = addr.startswith("G9FE1jSUU5SM3STv3PEx2kVYv5xeB5KyFh385Xgwwi9TBVBSQo6SqX7hzn4g17aJkWHhgSgnzYqgJggp2uJpHoNR13CzeqC")
            items = []
            blocks_found = 0
            mined_total = 0
            dev_total = 0
            for kind in ("in", "out", "pending", "pool"):
                for t in tr.get(kind, []):
                    is_block = t.get("type") == "block"
                    amounts = t.get("amounts") or [t.get("amount", 0)]
                    found = False
                    if is_block:
                        # the dev wallet gets 1 output in every block; 2 means we mined it
                        found = len(amounts) >= 2 if is_dev else True
                        if found:
                            blocks_found += 1
                            mined_total += max(amounts)
                            dev_total += sum(amounts) - max(amounts)
                        else:
                            dev_total += sum(amounts)
                    items.append({
                        "kind": "mined" if found else ("devfund" if is_block else kind),
                        "amount": t.get("amount", 0) / ATOMIC,
                        "height": t.get("height", 0),
                        "time": t.get("timestamp", 0),
                        "txid": t.get("txid", ""),
                        "fee": t.get("fee", 0) / ATOMIC,
                        "confirmations": t.get("confirmations", 0),
                        "locked": kind == "in" and t.get("confirmations", 0) < (60 if is_block else 10),
                    })
            items.sort(key=lambda x: (x["height"] or 10 ** 12, x["time"]), reverse=True)
            out["wallet"] = {
                "file": STATE["wallet_file"],
                "address": addr,
                "balance": bal["balance"] / ATOMIC,
                "unlocked": bal["unlocked_balance"] / ATOMIC,
                "blocks_to_unlock": bal.get("blocks_to_unlock", 0),
                "height": height,
                "blocks_found": blocks_found,
                "mined_total": mined_total / ATOMIC,
                "dev_total": dev_total / ATOMIC,
                "is_dev": is_dev,
                "history": items[:60],
            }
        except Exception as e:
            out["wallet"] = {"error": str(e), "file": STATE["wallet_file"]}
    return out


def api_mining(body):
    action = body.get("action")
    if action == "stop":
        r = daemon_other("stop_mining")
    elif action == "start":
        if not STATE["wallet_file"]:
            raise RpcError("افتح محفظتك الأول، المكافآت بتروح على عنوانها")
        addr = wallet("get_address", {"account_index": 0})["address"]
        threads = max(1, min(int(body.get("threads", 2)), os.cpu_count() or 64))
        r = daemon_other("start_mining", {"miner_address": addr, "threads_count": threads,
                                           "do_background_mining": False, "ignore_battery": True})
    else:
        raise RpcError("أمر غير معروف")
    if r.get("status") != "OK":
        msg = r.get("status", "error")
        if msg == "BUSY":
            msg = "الشبكة لسه بتتزامن، جرّب كمان شوية"
        raise RpcError(msg)
    return {"ok": True}


def api_send(body):
    if not STATE["wallet_file"]:
        raise RpcError("المحفظة مقفولة")
    address = body.get("address", "").strip()
    amount = to_atomic(body.get("amount", ""))
    v = wallet("validate_address", {"address": address})
    if not v.get("valid"):
        raise RpcError("عنوان Grox غير صحيح")
    try:
        r = wallet("transfer", {"destinations": [{"amount": amount, "address": address}],
                                "priority": 0, "get_tx_key": True}, timeout=180)
    except RpcError as e:
        if "not enough outputs to use" in str(e):
            raise RpcError("الشبكة لسه صغيرة على إخفاء التحويل وسط عملات أقدم. كمّل تعدين شوية وجرّب تاني.")
        if "not enough money" in str(e).lower() or "unlocked" in str(e).lower():
            raise RpcError("الرصيد المتاح مش كفاية (العملات المعدّنة بتتفتح بعد 60 بلوك)")
        raise
    return {"txid": r.get("tx_hash"), "fee": r.get("fee", 0) / ATOMIC, "amount": r.get("amount", 0) / ATOMIC}


def node_failed():
    return RpcError("الشبكة (groxd) مشتغلتش. التفاصيل في: " + CFG.node_log)


def api_node_start(_body):
    with NODE_LOCK:
        if daemon_up():
            return {"ok": True, "already": True}
        exe = os.path.join(CFG.bin_dir, "groxd" + EXE)
        if not os.path.exists(exe):
            raise RpcError(f"groxd{EXE} is missing from {CFG.bin_dir}. Reinstall Grox.")
        args = ["--non-interactive"] + CFG.node_args
        if CFG.testnet:
            args.append("--testnet")
        if CFG.manage_node or IS_WIN:
            # runs as our child (Windows has no --detach): hidden, stopped when the app closes
            proc = STATE["node_proc"] = _spawn([exe] + args)
        else:
            proc = None
            subprocess.Popen([exe, "--detach"] + args, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL).wait(timeout=60)
        for _ in range(180):
            if daemon_up():
                return {"ok": True}
            if proc is not None and proc.poll() is not None:
                break
            time.sleep(1)
        raise node_failed()


def api_node_stop(_body):
    daemon_other("stop_daemon")
    return {"ok": True}


def api_quit(_body):
    QUIT.set()
    return {"ok": True}


def mining_active():
    try:  # short timeout: the desktop app asks this while its window is closing
        return bool(_post(CFG.daemon + "/mining_status", {}, timeout=3).get("active"))
    except Exception:
        return False


def shutdown():
    """Close the wallet (it is saved) and, if this app started groxd, stop the node too."""
    stop_wallet_rpc()
    p = STATE["node_proc"]
    if p is None or p.poll() is not None:
        return
    try:
        daemon_other("stop_mining")
    except Exception:
        pass
    try:
        daemon_other("stop_daemon")
    except Exception:
        pass
    try:
        p.wait(timeout=90)  # groxd saves the blockchain before it exits
    except subprocess.TimeoutExpired:
        p.terminate()
    STATE["node_proc"] = None


ROUTES = {
    ("GET", "/api/wallets"): api_wallets,
    ("GET", "/api/state"): api_state,
    ("POST", "/api/open"): api_open,
    ("POST", "/api/create"): api_create,
    ("POST", "/api/restore"): api_restore,
    ("POST", "/api/lock"): api_lock,
    ("POST", "/api/mining"): api_mining,
    ("POST", "/api/send"): api_send,
    ("POST", "/api/node/start"): api_node_start,
    ("POST", "/api/node/stop"): api_node_stop,
    ("POST", "/api/quit"): api_quit,
}


# English versions of the (Arabic) error messages, picked when the page sends X-Lang: en
EN_ERRORS = {
    "المبلغ غير صحيح": "Invalid amount",
    "المبلغ لازم يكون أكبر من صفر": "Amount must be positive",
    "أقصى عدد أرقام بعد العلامة العشرية 11": "Too many decimals (max 11)",
    "المحفظة غير موجودة": "Wallet not found",
    "كلمة السر غلط": "Wrong password",
    "المحفظة مفتوحة في برنامج تاني (grox-wallet-cli أو نسخة قديمة من grox-wallet-rpc). اقفله الأول، أو اعمل ريستارت للجهاز.": "This wallet is open in another program (grox-wallet-cli or an old grox-wallet-rpc). Close it first, or restart the computer.",
    "افتح محفظتك الأول، المكافآت بتروح على عنوانها": "Open your wallet first, mining rewards go to its address",
    "الشبكة لسه بتتزامن، جرّب كمان شوية": "The node is still synchronizing, try again in a moment",
    "أمر غير معروف": "Unknown action",
    "المحفظة مقفولة": "Wallet is locked",
    "عنوان Grox غير صحيح": "Invalid Grox address",
    "الشبكة لسه صغيرة على إخفاء التحويل وسط عملات أقدم. كمّل تعدين شوية وجرّب تاني.": "The chain is still too young to hide your payment among older coins. Keep mining a while and try again.",
    "الرصيد المتاح مش كفاية (العملات المعدّنة بتتفتح بعد 60 بلوك)": "Not enough unlocked GROX (mined coins unlock after 60 blocks)",
    "الشبكة (groxd) مشتغلتش. التفاصيل في: ": "The Grox node (groxd) did not start. Details in: ",
    "مش قادر أوصل للشبكة أو المحفظة": "Node or wallet service is not reachable",
    "اسم المحفظة: حروف إنجليزي وأرقام و - و _ بس": "Wallet name: English letters, digits, - and _ only",
    "فيه محفظة بنفس الاسم، اختار اسم تاني": "A wallet with this name already exists, pick another name",
    "كلمة السر لازم 6 حروف على الأقل": "Password must be at least 6 characters",
    "لازم 25 كلمة بالظبط": "Exactly 25 words are needed",
    "الكلمات غير صحيحة، راجعها تاني": "Those words are not valid, check them again",
}


def translate_error(msg):
    if msg in EN_ERRORS:
        return EN_ERRORS[msg]
    for ar, en in EN_ERRORS.items():  # messages that end with a detail, e.g. a file path
        if ar.endswith(": ") and msg.startswith(ar):
            return en + msg[len(ar):]
    return msg


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, dict) and "error" in body and self.headers.get("X-Lang") == "en":
            body = {"error": translate_error(body["error"])}
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method):
        path = self.path.split("?")[0]
        if method == "GET" and path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        fn = ROUTES.get((method, path))
        if not fn:
            return self._send(404, {"error": "not found"})
        # websites can't send this header cross-origin without a CORS preflight we never answer
        if self.headers.get("X-Grox") != "1":
            return self._send(403, {"error": "forbidden"})
        body = {}
        if method == "POST":
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                try:
                    body = json.loads(self.rfile.read(n).decode())
                except ValueError:
                    return self._send(400, {"error": "bad json"})
        try:
            self._send(200, fn(body))
        except RpcError as e:
            self._send(400, {"error": str(e)})
        except urllib.error.URLError:
            self._send(503, {"error": "مش قادر أوصل للشبكة أو المحفظة"})
        except Exception as e:  # noqa
            self._send(500, {"error": str(e)})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def build_parser():
    ap = argparse.ArgumentParser(description="Grox Wallet app")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--bin-dir", default=os.path.join(HERE, "..", "..", "build", "bin"))
    ap.add_argument("--wallet-dir", default=default_wallet_dir(),
                    help="folder with your wallet files (default: home folder; C:\\Users\\<you>\\Grox on Windows)")
    ap.add_argument("--data-dir", default=None, help="groxd blockchain folder (default: groxd's own default)")
    ap.add_argument("--log-dir", default=None, help="folder for the wallet service log (default: wallet folder)")
    ap.add_argument("--node-args", default="",
                    help='extra groxd args for the "Start node" button, e.g. "--add-priority-node=1.2.3.4:19880"')
    ap.add_argument("--testnet", action="store_true")
    ap.add_argument("--regtest", action="store_true", help=argparse.SUPPRESS)
    return ap


def configure(args):
    global CFG
    CFG = Config(args)
    return CFG


def make_server(port):
    """Bind the local web server, or raise OSError when the port is busy."""
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    args = build_parser().parse_args()
    configure(args)
    import signal

    def _quit(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _quit)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _quit)
    try:
        srv = make_server(args.port)
    except OSError:
        print(f"Grox Wallet is already running (port {args.port} is busy).")
        print(f"Open http://localhost:{args.port} - or stop the old copy with: pkill -INT -f grox_app.py")
        sys.exit(1)
    print(f"Grox Wallet is running: open http://localhost:{srv.server_port} in your browser")
    print("Press Ctrl+C to quit (your wallet is saved and closed).")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while not QUIT.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        print("\nClosing wallet...")
        srv.shutdown()
        shutdown()


if __name__ == "__main__":
    main()
