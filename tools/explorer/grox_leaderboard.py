"""Opt-in blocks-found leaderboard for the Grox explorer (Python standard library only).

Miners register through the Telegram bot with a nickname, their address and their PRIVATE VIEW
KEY. The bot writes them to <dir>/miners.json. This scanner walks the chain, checks every block
reward against every registered miner (like a view-only wallet does) and keeps the results in
<dir>/scan.json. Only nicknames and block heights are ever published: addresses and view keys
never leave the server.
"""
import hashlib
import json
import os
import threading
import time

import grox_keys as K

RECHECK = 10            # always re-check the newest blocks, in case of a short reorg
MAX_EVENTS = 100


def _miner_id(address, view_key):
    return hashlib.sha256((address + ":" + view_key).encode()).hexdigest()[:16]


class Leaderboard:
    def __init__(self, directory, rpc, testnet=False):
        self.dir = directory
        self.rpc = rpc
        self.prefix = K.TESTNET_PREFIX if testnet else K.MAINNET_PREFIX
        self.registry_file = os.path.join(directory, "miners.json")
        self.state_file = os.path.join(directory, "scan.json")
        self.lock = threading.Lock()
        self.registry_mtime = None
        self.watchers = {}           # id -> {"nick", "watcher"}
        self.state = self._load(self.state_file, {"miners": {}, "events": []})
        self.top = 0
        self.busy = False

    # ------------------------------------------------------------ files
    @staticmethod
    def _load(path, default):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _save(self):
        tmp = self.state_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.state_file)

    def _reload_registry(self):
        try:
            mtime = os.stat(self.registry_file).st_mtime
        except OSError:
            mtime = None
        if mtime == self.registry_mtime:
            return
        self.registry_mtime = mtime
        reg = self._load(self.registry_file, {}).get("miners", {})
        watchers = {}
        for entry in reg.values():
            try:
                spend, view = K.parse_address(entry["address"], self.prefix)
                a = K.parse_view_key(entry["view_key"])
                if not K.view_key_matches(a, view):
                    continue
            except (KeyError, ValueError):
                continue
            mid = _miner_id(entry["address"], entry["view_key"])
            watchers[mid] = {"nick": entry["nick"], "watcher": K.Watcher(spend, a)}
        with self.lock:
            self.watchers = watchers
            miners = self.state["miners"]
            for mid, w in watchers.items():
                m = miners.setdefault(mid, {"heights": [], "scanned_to": 0, "backfilled": False})
                m["nick"] = w["nick"]
            for mid in [m for m in miners if m not in watchers]:
                del miners[mid]           # unregistered: forget their blocks too

    # ------------------------------------------------------------ scanning
    def _coinbase(self, height):
        r = self.rpc("get_block", {"height": height})
        j = json.loads(r["json"])
        mt = j["miner_tx"]
        main, _ = K.parse_extra_pubkeys(mt.get("extra", []))
        return main, K.miner_outputs(mt), r["block_header"]["timestamp"]

    def scan_once(self):
        self._reload_registry()
        if not self.watchers:
            return
        info = self.rpc("get_info")
        top = info["height"] - 1
        self.top = top
        with self.lock:
            miners = self.state["miners"]
            for m in miners.values():
                # re-check the newest blocks every round
                limit = max(0, top - RECHECK)
                if m["scanned_to"] > limit:
                    m["scanned_to"] = limit
                    m["heights"] = [h for h in m["heights"] if h <= limit]
            start = min(m["scanned_to"] for m in miners.values()) + 1
        self.busy = True
        changed = False
        try:
            for h in range(max(1, start), top + 1):
                miners = self.state["miners"]
                todo = [(mid, w) for mid, w in list(self.watchers.items())
                        if mid in miners and miners[mid]["scanned_to"] < h]
                if not todo:
                    continue
                tx_pub, outs, ts = self._coinbase(h)
                for mid, w in todo:
                    m = miners.get(mid)
                    if m is None:
                        continue
                    if tx_pub and outs:
                        d = w["watcher"].derivation(tx_pub)
                        if d and any(w["watcher"].owns(d, i, key, tag) for i, key, tag in outs):
                            with self.lock:
                                if h not in m["heights"]:
                                    m["heights"].append(h)
                                    first_ever = not m.get("ever_found")
                                    m["ever_found"] = True    # survives the re-check of recent blocks
                                    if m["backfilled"] and first_ever and h > top - 60:
                                        eid = self.state.get("next_event_id", 1)
                                        self.state["next_event_id"] = eid + 1
                                        self.state["events"].append({"id": eid, "type": "first_block",
                                                                     "nick": w["nick"], "height": h, "time": ts})
                                        self.state["events"] = self.state["events"][-MAX_EVENTS:]
                    m["scanned_to"] = h
                changed = True
                if h % 500 == 0:
                    self._save()
            with self.lock:
                for m in self.state["miners"].values():
                    if m["scanned_to"] >= top:
                        m["backfilled"] = True
        finally:
            self.busy = False
        if changed:
            self._save()

    def run_forever(self, every=20):
        while True:
            try:
                self.scan_once()
            except Exception as ex:      # node restarting, bad block data, ...
                print("leaderboard scan error:", repr(ex)[:200], flush=True)
            time.sleep(every)

    def start(self):
        threading.Thread(target=self.run_forever, daemon=True).start()

    # ------------------------------------------------------------ public views (nicknames only)
    def table(self):
        with self.lock:
            rows = []
            day_ago = self.top - 1440
            for m in self.state["miners"].values():
                hs = sorted(m["heights"])
                rows.append({
                    "nick": m.get("nick", "?"), "blocks": len(hs),
                    "blocks_24h": sum(1 for h in hs if h > day_ago),
                    "first_block": hs[0] if hs else None, "last_block": hs[-1] if hs else None,
                    "synced": m.get("backfilled", False),
                })
        rows.sort(key=lambda r: (-r["blocks"], -(r["last_block"] or 0), r["nick"].lower()))
        return {"miners": rows[:200], "registered": len(rows), "scanned_height": self.top,
                "syncing": any(not r["synced"] for r in rows)}

    def found_by(self, height):
        with self.lock:
            for m in self.state["miners"].values():
                if height in m["heights"]:
                    return m.get("nick")
        return None

    def events(self, since=0):
        """Events with an id above `since` (ids only grow, so a client never misses or repeats one)."""
        with self.lock:
            return [e for e in self.state["events"] if e.get("id", 0) > since]
