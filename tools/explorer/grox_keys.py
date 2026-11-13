"""Grox key helpers for the opt-in blocks-found leaderboard (Python standard library only).

A miner who wants their nickname on the leaderboard shares their address and PRIVATE VIEW KEY.
With those, this module can tell which block rewards were paid to that address, the same way
a view-only wallet does. A view key can only see incoming payments; it can never spend coins.

Implements the small part of CryptoNote/Monero cryptography that this needs:
Keccak-256, ed25519 group operations, Monero base58 addresses, key derivation and the
coinbase output check (including view tags).
"""

# ---------------------------------------------------------------- Keccak-256 (original padding)

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M64 = (1 << 64) - 1


def _rol(v, n):
    return ((v << n) | (v >> (64 - n))) & _M64 if n else v


def _keccak_f(A):
    for rc in _RC:
        C = [A[x][0] ^ A[x][1] ^ A[x][2] ^ A[x][3] ^ A[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rol(C[(x + 1) % 5], 1) for x in range(5)]
        A = [[A[x][y] ^ D[x] for y in range(5)] for x in range(5)]
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rol(A[x][y], _ROT[x][y])
        A = [[B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        A[0][0] ^= rc
    return A


def keccak256(data: bytes) -> bytes:
    rate = 136
    msg = bytearray(data) + b"\x01"
    msg += b"\x00" * ((-len(msg)) % rate)
    msg[-1] |= 0x80
    A = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(rate // 8):
            x, y = i % 5, i // 5
            A[x][y] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        A = _keccak_f(A)
    out = b"".join(A[i % 5][i // 5].to_bytes(8, "little") for i in range(4))
    return out


# ---------------------------------------------------------------- ed25519

P = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, P - 2, P)) % P
_I = pow(2, (P - 1) // 4, P)


def _recover_x(y, sign):
    xx = (y * y - 1) * pow(_D * y * y + 1, P - 2, P) % P
    x = pow(xx, (P + 3) // 8, P)
    if (x * x - xx) % P:
        x = x * _I % P
    if (x * x - xx) % P:
        return None
    if x & 1 != sign:
        x = P - x
    if x == 0 and sign:
        return None
    return x


_GY = 4 * pow(5, P - 2, P) % P
_GX = _recover_x(_GY, 0)
G = (_GX, _GY, 1, _GX * _GY % P)       # extended coordinates (X, Y, Z, T)
ZERO = (0, 1, 1, 0)


def _add(p, q):
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = 2 * t1 * t2 * _D % P
    d = 2 * z1 * z2 % P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _double(p):
    x1, y1, z1, _ = p
    a = x1 * x1 % P
    b = y1 * y1 % P
    c = 2 * z1 * z1 % P
    h = a + b
    e = h - (x1 + y1) * (x1 + y1)
    g = a - b
    f = c + g
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def scalarmult(p, n):
    """n*p for any point p (double-and-add, 4-bit window)."""
    n %= L
    if n == 0:
        return ZERO
    table = [ZERO, p]
    for _ in range(14):
        table.append(_add(table[-1], p))
    q = ZERO
    for shift in range((n.bit_length() + 3) // 4 * 4 - 4, -1, -4):
        q = _double(_double(_double(_double(q))))
        w = (n >> shift) & 15
        if w:
            q = _add(q, table[w])
    return q


_G_POW = []          # 2^i * G, filled on first use


def scalarmult_base(n):
    n %= L
    if not _G_POW:
        q = G
        for _ in range(253):
            _G_POW.append(q)
            q = _double(q)
    q = ZERO
    i = 0
    while n:
        if n & 1:
            q = _add(q, _G_POW[i])
        n >>= 1
        i += 1
    return q


def mul8(p):
    return _double(_double(_double(p)))


def encode_point(p) -> bytes:
    x, y, z, _ = p
    zi = pow(z, P - 2, P)
    x, y = x * zi % P, y * zi % P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def decode_point(b: bytes):
    if len(b) != 32:
        return None
    v = int.from_bytes(b, "little")
    y = v & ((1 << 255) - 1)
    if y >= P:
        return None
    x = _recover_x(y, v >> 255)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


def sc_reduce32(b: bytes) -> int:
    return int.from_bytes(b, "little") % L


def hash_to_scalar(data: bytes) -> int:
    return sc_reduce32(keccak256(data))


def varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


# ---------------------------------------------------------------- addresses (Monero base58)

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {c: i for i, c in enumerate(_B58)}
_FULL_BLOCK, _FULL_ENC = 8, 11
_ENC_SIZES = [0, 2, 3, 5, 6, 7, 9, 10, 11]

MAINNET_PREFIX = 90      # standard 'G' address (integrated = 91, subaddress = 92)
TESTNET_PREFIX = 108     # 'K'


def b58decode(s: str) -> bytes:
    out = bytearray()
    for i in range(0, len(s), _FULL_ENC):
        chunk = s[i:i + _FULL_ENC]
        if len(chunk) not in _ENC_SIZES:
            raise ValueError("bad base58 length")
        size = _ENC_SIZES.index(len(chunk))
        num = 0
        for c in chunk:
            if c not in _B58_IDX:
                raise ValueError("bad base58 character")
            num = num * 58 + _B58_IDX[c]
        if num >= 1 << (8 * size):
            raise ValueError("bad base58 block")
        out += num.to_bytes(size, "big")
    return bytes(out)


def _read_varint(b: bytes):
    n, shift = 0, 0
    for i, byte in enumerate(b):
        n |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return n, i + 1
        shift += 7
        if shift > 63:
            break
    raise ValueError("bad varint")


def parse_address(addr: str, prefix=MAINNET_PREFIX):
    """Return (spend_public, view_public) as 32-byte strings for a standard Grox address."""
    addr = addr.strip()
    raw = b58decode(addr)
    tag, n = _read_varint(raw)
    if tag != prefix:
        raise ValueError("not a standard Grox address (subaddresses and integrated addresses are not supported)")
    body, checksum = raw[:-4], raw[-4:]
    if keccak256(body)[:4] != checksum:
        raise ValueError("address checksum is wrong")
    keys = raw[n:-4]
    if len(keys) != 64:
        raise ValueError("wrong address length")
    spend, view = keys[:32], keys[32:]
    if decode_point(spend) is None or decode_point(view) is None:
        raise ValueError("invalid key in address")
    return spend, view


def parse_view_key(hexkey: str) -> int:
    hexkey = hexkey.strip().lower()
    if len(hexkey) != 64 or any(c not in "0123456789abcdef" for c in hexkey):
        raise ValueError("the private view key is 64 hex characters")
    k = int.from_bytes(bytes.fromhex(hexkey), "little")
    if k >= L or k == 0:
        raise ValueError("not a valid private view key")
    return k


def view_key_matches(view_secret: int, view_public: bytes) -> bool:
    return encode_point(scalarmult_base(view_secret)) == view_public


# ---------------------------------------------------------------- coinbase ownership

def parse_extra_pubkeys(extra):
    """Main tx public key and additional tx public keys from a tx extra (list of ints)."""
    ex = bytes(extra)
    i, main, additional = 0, None, []
    while i < len(ex):
        tag = ex[i]
        i += 1
        if tag == 0x01:
            main = ex[i:i + 32]
            i += 32
        elif tag == 0x02:
            n = ex[i]
            i += 1 + n
        elif tag == 0x04:
            count, used = _read_varint(ex[i:])
            i += used
            additional = [ex[i + 32 * k:i + 32 * k + 32] for k in range(count)]
            i += 32 * count
        elif tag == 0x00:
            break
        else:
            break
    return main, additional


class Watcher:
    """One registered miner: address spend key + private view key."""

    def __init__(self, spend_public: bytes, view_secret: int):
        self.spend = decode_point(spend_public)
        self.a = view_secret

    def derivation(self, tx_pub: bytes):
        R = decode_point(tx_pub)
        if R is None:
            return None
        return encode_point(mul8(scalarmult(R, self.a)))

    def owns(self, derivation: bytes, index: int, out_key: bytes, view_tag=None) -> bool:
        idx = varint(index)
        if view_tag is not None and keccak256(b"view_tag" + derivation + idx)[0] != view_tag:
            return False
        s = hash_to_scalar(derivation + idx)
        return encode_point(_add(scalarmult_base(s), self.spend)) == out_key


def miner_outputs(miner_tx: dict):
    """(index, out_key bytes, view_tag or None) for each miner output (the last one is the dev fund)."""
    outs = []
    vout = miner_tx.get("vout", [])
    for i, o in enumerate(vout[:-1] if len(vout) >= 2 else vout):
        tgt = o.get("target", {})
        if "tagged_key" in tgt:
            outs.append((i, bytes.fromhex(tgt["tagged_key"]["key"]), int(tgt["tagged_key"]["view_tag"], 16)))
        elif "key" in tgt:
            outs.append((i, bytes.fromhex(tgt["key"]), None))
    return outs
