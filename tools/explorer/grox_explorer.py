#!/usr/bin/env python3
"""Grox block explorer - read-only web explorer for a groxd node.

    python3 tools/explorer/grox_explorer.py            # http://localhost:8792
    python3 tools/explorer/grox_explorer.py --public    # listen on all interfaces (for a server)

Only read-only RPC calls are made, so it is safe to expose publicly.
Only the Python standard library is used.
"""
import argparse
import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ATOMIC = 10 ** 11
HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON = "http://127.0.0.1:19881"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class NotFound(Exception):
    pass


def _post(path, payload, timeout=20):
    req = urllib.request.Request(DAEMON + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def rpc(method, params=None):
    r = _post("/json_rpc", {"jsonrpc": "2.0", "id": 0, "method": method, "params": params or {}})
    if "error" in r:
        raise NotFound(r["error"].get("message", "error"))
    return r["result"]


# tiny TTL cache so a busy page can't hammer the node
_cache = {}
_cache_lock = threading.Lock()


def cached(key, ttl, fn):
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _cache_lock:
        _cache[key] = (now, val)
        if len(_cache) > 2000:
            for k in sorted(_cache, key=lambda k: _cache[k][0])[:1000]:
                _cache.pop(k, None)
    return val


def g(x):
    return x / ATOMIC


def header_view(h):
    return {
        "height": h["height"], "hash": h["hash"], "timestamp": h["timestamp"],
        "difficulty": h["difficulty"], "reward": g(h["reward"]), "size": h.get("block_weight") or h.get("block_size"),
        "txs": h["num_txes"], "version": f'{h["major_version"]}.{h["minor_version"]}',
        "nonce": h["nonce"], "prev_hash": h["prev_hash"], "depth": h.get("depth", 0),
        "orphan": h.get("orphan_status", False),
    }


def api_info(_q):
    def f():
        i = rpc("get_info")
        last = rpc("get_last_block_header")["block_header"]
        pool = _post("/get_transaction_pool_stats", {}).get("pool_stats", {})
        return {
            "height": i["height"], "difficulty": i["difficulty"],
            "hashrate": round(i["difficulty"] / max(i.get("target", 60), 1)),
            "tx_count": i.get("tx_count", 0), "mempool": pool.get("txs_total", i.get("tx_pool_size", 0)),
            "peers": i.get("incoming_connections_count", 0) + i.get("outgoing_connections_count", 0),
            "network": i.get("nettype", "mainnet"), "version": i.get("version", ""),
            "reward": g(last["reward"]), "last_block_time": last["timestamp"],
            "supply_mined": None,
        }
    return cached("info", 5, f)


def api_blocks(q):
    info = api_info(q)
    top = info["height"] - 1
    count = max(1, min(int(q.get("count", ["25"])[0]), 50))
    start = int(q.get("before", [str(top + 1)])[0]) - 1
    start = min(start, top)
    end = max(0, start - count + 1)
    if start < 0:
        return {"blocks": [], "top": top}

    def f():
        hs = rpc("get_block_headers_range", {"start_height": end, "end_height": start})["headers"]
        return [header_view(h) for h in reversed(hs)]
    # older ranges never change; the newest page changes every block
    ttl = 5 if start >= top - 1 else 600
    return {"blocks": cached(f"blocks:{end}:{start}", ttl, f), "top": top}


def _tx_details(hashes):
    if not hashes:
        return []
    r = _post("/get_transactions", {"txs_hashes": hashes, "decode_as_json": True})
    out = []
    for t in r.get("txs", []):
        j = json.loads(t["as_json"]) if t.get("as_json") else {}
        rct = j.get("rct_signatures", {}) or {}
        vin = j.get("vin", [])
        ring = len(vin[0]["key"]["key_offsets"]) if vin and "key" in vin[0] else 0
        out.append({
            "hash": t["tx_hash"], "fee": g(rct.get("txnFee", 0)), "inputs": len(vin), "ring_size": ring,
            "outputs": len(j.get("vout", [])), "size": len(t.get("as_hex", "")) // 2,
            "in_pool": t.get("in_pool", False), "height": t.get("block_height"),
            "timestamp": t.get("block_timestamp"), "version": j.get("version"),
            "unlock_time": j.get("unlock_time", 0),
        })
    return out


def api_block(q):
    ident = q.get("id", [""])[0].strip()
    if ident.isdigit():
        params = {"height": int(ident)}
    elif HEX64.match(ident):
        params = {"hash": ident.lower()}
    else:
        raise NotFound("bad id")

    def f():
        r = rpc("get_block", params)
        h = header_view(r["block_header"])
        j = json.loads(r["json"])
        mt = j["miner_tx"]
        outs = [g(o["amount"]) for o in mt["vout"]]
        h["coinbase"] = {
            "hash": r["block_header"].get("miner_tx_hash") or r.get("miner_tx_hash"),
            "outputs": outs,
            # from block 2 the last coinbase output is the dev fund (consensus rule)
            "dev_fund": outs[-1] if h["height"] >= 2 and len(outs) >= 2 else 0,
            "miner": sum(outs[:-1]) if h["height"] >= 2 and len(outs) >= 2 else sum(outs),
            "unlock_height": mt.get("unlock_time", 0),
        }
        h["transactions"] = _tx_details(j.get("tx_hashes", []))
        h["next_height"] = h["height"] + 1
        return h
    blk = cached(f"block:{ident}", 30, f)
    blk = dict(blk)
    blk["confirmations"] = api_info(q)["height"] - blk["height"]
    return blk


def api_tx(q):
    ident = q.get("id", [""])[0].strip().lower()
    if not HEX64.match(ident):
        raise NotFound("bad id")

    def f():
        r = _post("/get_transactions", {"txs_hashes": [ident], "decode_as_json": True})
        if not r.get("txs"):
            raise NotFound("tx not found")
        t = r["txs"][0]
        j = json.loads(t["as_json"])
        d = _tx_details([ident])[0]
        coinbase = bool(j.get("vin")) and "gen" in j["vin"][0]
        d["coinbase"] = coinbase
        d["output_amounts"] = [g(o["amount"]) for o in j.get("vout", [])] if coinbase else []
        d["key_images"] = [v["key"]["k_image"] for v in j.get("vin", []) if "key" in v]
        d["output_keys"] = [o["target"]["tagged_key"]["key"] if "tagged_key" in o["target"] else o["target"].get("key")
                            for o in j.get("vout", [])]
        return d
    tx = dict(cached(f"tx:{ident}", 10, f))
    h = api_info(q)["height"]
    tx["confirmations"] = (h - tx["height"]) if tx.get("height") and not tx.get("in_pool") else 0
    return tx


def api_mempool(_q):
    def f():
        r = _post("/get_transaction_pool", {})
        out = []
        for t in r.get("transactions", [])[:100]:
            out.append({"hash": t["id_hash"], "fee": g(t.get("fee", 0)), "size": t.get("blob_size", 0),
                        "received": t.get("receive_time", 0)})
        return out
    return {"txs": cached("mempool", 5, f)}


def api_search(q):
    s = q.get("q", [""])[0].strip()
    if s.isdigit():
        return {"type": "block", "id": s}
    if HEX64.match(s):
        try:
            rpc("get_block_header_by_hash", {"hash": s.lower()})
            return {"type": "block", "id": s.lower()}
        except Exception:
            pass
        r = _post("/get_transactions", {"txs_hashes": [s.lower()]})
        if r.get("txs"):
            return {"type": "tx", "id": s.lower()}
    raise NotFound("nothing found")


ROUTES = {"/api/info": api_info, "/api/blocks": api_blocks, "/api/block": api_block,
          "/api/tx": api_tx, "/api/mempool": api_mempool, "/api/search": api_search}

# simple per-IP rate limit (requests per 10 s)
_hits = {}
_hits_lock = threading.Lock()


def allowed(ip, limit=60):
    now = time.time()
    with _hits_lock:
        lst = [t for t in _hits.get(ip, []) if now - t < 10]
        lst.append(now)
        _hits[ip] = lst
        if len(_hits) > 5000:
            _hits.clear()
        return len(lst) <= limit


class Handler(BaseHTTPRequestHandler):
    server_version = "GroxExplorer"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json", cache="no-store"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        ip = self.headers.get("CloudFront-Viewer-Address", self.client_address[0]).split(":")[0]
        if not allowed(ip):
            return self._send(429, {"error": "slow down"})
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8", "public, max-age=60")
        fn = ROUTES.get(u.path)
        if not fn:
            return self._send(404, {"error": "not found"})
        try:
            self._send(200, fn(parse_qs(u.query)))
        except NotFound as e:
            self._send(404, {"error": str(e)})
        except (ValueError, KeyError):
            self._send(400, {"error": "bad request"})
        except Exception:
            self._send(503, {"error": "node unavailable"})


def main():
    global DAEMON
    ap = argparse.ArgumentParser(description="Grox block explorer")
    ap.add_argument("--port", type=int, default=8792)
    ap.add_argument("--public", action="store_true", help="listen on 0.0.0.0 instead of 127.0.0.1")
    ap.add_argument("--daemon", default=None, help="groxd RPC URL (default http://127.0.0.1:19881)")
    ap.add_argument("--testnet", action="store_true")
    a = ap.parse_args()
    DAEMON = a.daemon or ("http://127.0.0.1:29881" if a.testnet else "http://127.0.0.1:19881")
    host = "0.0.0.0" if a.public else "127.0.0.1"
    try:
        srv = ThreadingHTTPServer((host, a.port), Handler)
    except OSError:
        print(f"Port {a.port} is busy - is the explorer already running? (pkill -f grox_explorer.py)")
        raise SystemExit(1)
    print(f"Grox explorer: http://localhost:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
