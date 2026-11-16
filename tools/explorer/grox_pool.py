"""Pool explorer for the public Grox P2Pool node (Python standard library only).

Reads the files the Grox P2Pool port writes into its --data-api folder:
  pool/shares         newest shares on the share chain (id, height, time, difficulty, address)
  pool/window         current PPLNS window: weight and share count per address
  pool/payouts.jsonl  one line per pool block: finder and the amount paid to each address
  pool/blocks         pool blocks (height, hash, time), also the ones from before payouts were recorded

and keeps a small SQLite index so every miner can look up their own numbers by address.

Privacy: P2Pool share chains are public by design (each share carries its miner's address), so
nothing here is secret. Still, lists only ever show shortened addresses; full details are shown
only to someone who already knows the full address. No IPs are stored.
"""
import json
import os
import re
import sqlite3
import threading
import time

import grox_keys as K

MATURITY = 60                 # blocks before a coinbase output can be spent
KEEP_SHARES_DAYS = 30
ADDR_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{95}$")


def short(addr):
    return addr[:6] + "…" + addr[-4:] if addr else ""


class PoolIndex:
    def __init__(self, api_dir, db_path, rpc, testnet=False):
        self.api = api_dir
        self.rpc = rpc
        self.prefix = K.TESTNET_PREFIX if testnet else K.MAINNET_PREFIX
        self.db_path = db_path
        self.lock = threading.Lock()
        self.window = {"miners": [], "tip": 0, "bottom": 0, "ts": 0}
        self.chain_height = 0
        self.reward = 0
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS shares(id TEXT PRIMARY KEY, h INTEGER, ts INTEGER, d INTEGER, u INTEGER, w TEXT);
            CREATE INDEX IF NOT EXISTS shares_w ON shares(w, ts);
            CREATE INDEX IF NOT EXISTS shares_ts ON shares(ts);
            CREATE TABLE IF NOT EXISTS blocks(height INTEGER, hash TEXT PRIMARY KEY, ts INTEGER, finder TEXT,
                reward INTEGER, dev INTEGER, sidechain_height INTEGER, recorded INTEGER, status TEXT);
            CREATE INDEX IF NOT EXISTS blocks_h ON blocks(height);
            CREATE TABLE IF NOT EXISTS payouts(hash TEXT, height INTEGER, w TEXT, amount INTEGER, PRIMARY KEY(hash, w));
            CREATE INDEX IF NOT EXISTS payouts_w ON payouts(w, height);
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
        """)
        os.chmod(db_path, 0o600)

    # ------------------------------------------------------------ indexing
    def _read(self, *parts):
        with open(os.path.join(self.api, *parts)) as f:
            return json.load(f)

    def _meta(self, k, default=None):
        r = self.db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    def _set_meta(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))

    def _index_shares(self):
        try:
            shares = self._read("pool", "shares")
        except (OSError, ValueError):
            return
        self.db.executemany("INSERT OR IGNORE INTO shares VALUES(?,?,?,?,?,?)",
                            [(s["id"], s["h"], s["ts"], int(s["d"]), s["u"], s["w"]) for s in shares])

    def _index_payouts(self):
        path = os.path.join(self.api, "pool", "payouts.jsonl")
        try:
            size = os.path.getsize(path)
        except OSError:
            return
        pos = int(self._meta("payouts_pos", 0))
        if size < pos:            # file replaced
            pos = 0
        with open(path) as f:
            f.seek(pos)
            while True:
                line = f.readline()
                if not line.endswith("\n"):
                    break         # partial line: read it next time
                pos = f.tell()
                try:
                    b = json.loads(line)
                except ValueError:
                    continue
                self.db.execute("INSERT OR REPLACE INTO blocks VALUES(?,?,?,?,?,?,?,1,COALESCE((SELECT status FROM blocks WHERE hash=?),'pending'))",
                                (b["height"], b["hash"], b["ts"], b["finder"], b["reward"], b["dev"],
                                 b.get("sidechainHeight"), b["hash"]))
                self.db.executemany("INSERT OR REPLACE INTO payouts VALUES(?,?,?,?)",
                                    [(b["hash"], b["height"], w, a) for w, a in b["payouts"]])
        self._set_meta("payouts_pos", pos)

    def _index_found_blocks(self):
        try:
            blocks = self._read("pool", "blocks")
        except (OSError, ValueError):
            return
        for b in blocks:
            self.db.execute("INSERT OR IGNORE INTO blocks VALUES(?,?,?,NULL,NULL,NULL,NULL,0,'pending')",
                            (b["height"], b["hash"], b["ts"]))

    def _check_chain(self):
        """Mark pool blocks as orphaned if the main chain has a different block at that height,
        and fill in the reward of blocks found before payouts were recorded."""
        last = self.rpc("get_last_block_header")["block_header"]
        self.chain_height = last["height"]
        self.reward = last["reward"]
        rows = self.db.execute("SELECT height, hash, reward FROM blocks WHERE status='pending' OR reward IS NULL").fetchall()
        for height, h, reward in rows:
            if height > self.chain_height:
                continue
            hdr = self.rpc("get_block_header_by_height", {"height": height})["block_header"]
            if hdr["hash"] != h:
                self.db.execute("UPDATE blocks SET status='orphan' WHERE hash=?", (h,))
                continue
            if reward is None:
                self.db.execute("UPDATE blocks SET reward=? WHERE hash=?", (hdr["reward"], h))
            if self.chain_height - height >= MATURITY:
                self.db.execute("UPDATE blocks SET status='ok' WHERE hash=?", (h,))

    def scan_once(self):
        try:
            window = self._read("pool", "window")
        except (OSError, ValueError):
            window = None
        with self.lock:
            if window:
                self.window = window
            self._index_shares()
            self._index_payouts()
            self._index_found_blocks()
            self._check_chain()
            self.db.execute("DELETE FROM shares WHERE ts < ?", (int(time.time()) - KEEP_SHARES_DAYS * 86400,))
            self.db.commit()

    def run_forever(self, every=15):
        while True:
            try:
                self.scan_once()
            except Exception as ex:      # node restarting, P2Pool writing a file, ...
                print("pool index error:", repr(ex)[:200], flush=True)
            time.sleep(every)

    def start(self):
        threading.Thread(target=self.run_forever, daemon=True).start()

    # ------------------------------------------------------------ public views
    def _status(self, height, status):
        if status == "orphan":
            return "orphan"
        left = MATURITY - (self.chain_height - height)
        return "unlocked" if left <= 0 else f"{left} to unlock"

    def blocks(self, limit=50, before=None):
        limit = max(1, min(int(limit), 100))
        with self.lock:
            q = "SELECT height, hash, ts, finder, reward, dev, recorded, status FROM blocks"
            args = []
            if before:
                q += " WHERE height < ?"
                args.append(int(before))
            q += " ORDER BY height DESC LIMIT ?"
            args.append(limit)
            rows = self.db.execute(q, args).fetchall()
            out = []
            for height, h, ts, finder, reward, dev, recorded, status in rows:
                n = self.db.execute("SELECT COUNT(*) FROM payouts WHERE hash=?", (h,)).fetchone()[0]
                out.append({"height": height, "hash": h, "ts": ts, "finder": short(finder),
                            "reward": reward, "dev": dev, "miners_paid": n if recorded else None,
                            "status": self._status(height, status)})
            total = self.db.execute("SELECT COUNT(*) FROM blocks WHERE status!='orphan'").fetchone()[0]
        return {"blocks": out, "total": total, "chain_height": self.chain_height}

    def block(self, h):
        with self.lock:
            r = self.db.execute("SELECT height, hash, ts, finder, reward, dev, recorded, status FROM blocks WHERE hash=? OR height=?",
                                (h, int(h) if str(h).isdigit() else -1)).fetchone()
            if not r:
                return None
            pays = self.db.execute("SELECT w, amount FROM payouts WHERE hash=? ORDER BY amount DESC", (r[1],)).fetchall()
        return {"height": r[0], "hash": r[1], "ts": r[2], "finder": short(r[3]), "reward": r[4], "dev": r[5],
                "recorded": bool(r[6]), "status": self._status(r[0], r[7]),
                "payouts": [{"miner": short(w), "amount": a} for w, a in pays]}

    def valid_address(self, addr):
        if not addr or not ADDR_RE.match(addr):
            return False
        try:
            K.parse_address(addr, self.prefix)
            return True
        except Exception:
            return False

    def miner(self, addr):
        now = int(time.time())
        with self.lock:
            win = self.window.get("miners", [])
            total_w = sum(int(m["weight"]) for m in win) or 1
            mine = next((m for m in win if m["w"] == addr), None)
            pct = int(mine["weight"]) / total_w if mine else 0.0

            first = self.db.execute("SELECT MIN(ts) FROM shares").fetchone()[0] or now

            def hashrate(seconds):
                # shares only exist since the index started: don't divide by time we haven't seen
                period = max(60, min(seconds, now - first))
                d = self.db.execute("SELECT COALESCE(SUM(d),0) FROM shares WHERE w=? AND ts>=?", (addr, now - period)).fetchone()[0]
                return round(d / period)

            s24 = self.db.execute("SELECT COUNT(*), MAX(ts) FROM shares WHERE w=? AND ts>=?", (addr, now - 86400)).fetchone()
            last_share = self.db.execute("SELECT MAX(ts) FROM shares WHERE w=?", (addr,)).fetchone()[0]
            pays = self.db.execute(
                "SELECT p.height, p.hash, b.ts, p.amount, b.status FROM payouts p JOIN blocks b ON b.hash=p.hash "
                "WHERE p.w=? ORDER BY p.height DESC LIMIT 100", (addr,)).fetchall()
            tot = self.db.execute(
                "SELECT COUNT(*), COALESCE(SUM(p.amount),0) FROM payouts p JOIN blocks b ON b.hash=p.hash "
                "WHERE p.w=? AND b.status!='orphan'", (addr,)).fetchone()
            found = [r[0] for r in self.db.execute(
                "SELECT height FROM blocks WHERE finder=? AND status!='orphan' ORDER BY height DESC LIMIT 100", (addr,))]
            miner_reward = self.reward * 95 // 100 if self.reward else 0
        return {
            "address": short(addr),
            "known": bool(mine or last_share or pays),
            "window": {"shares": mine["shares"] if mine else 0, "weight": int(mine["weight"]) if mine else 0,
                       "percent": round(pct * 100, 3), "next_payout": int(miner_reward * pct),
                       "miners": len(win)},
            "hashrate": {"15m": hashrate(900), "1h": hashrate(3600), "24h": hashrate(86400)},
            "shares_24h": s24[0], "last_share": last_share,
            "paid": {"blocks": tot[0], "total": tot[1]},
            "payouts": [{"height": h, "hash": hh, "ts": ts, "amount": a, "status": self._status(h, st)}
                        for h, hh, ts, a, st in pays],
            "blocks_found": found,
        }
