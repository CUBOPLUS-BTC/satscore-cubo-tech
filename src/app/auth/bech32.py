"""Minimal bech32 encoding for LNURL (BIP-173 reference implementation)."""

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values: list[int]) -> int:
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _convertbits(
    data: bytes, frombits: int, tobits: int, pad: bool = True
) -> list[int]:
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return []
    return ret


def bech32_encode(hrp: str, data: bytes) -> str:
    """Encode bytes as bech32 with the given human-readable part."""
    conv = _convertbits(data, 8, 5)
    combined = conv + _bech32_create_checksum(hrp, conv)
    return hrp + "1" + "".join([CHARSET[d] for d in combined])


def lnurl_encode(url: str) -> str:
    """Encode a URL as an LNURL (bech32-encoded with 'lnurl' HRP)."""
    return bech32_encode("lnurl", url.encode("utf-8")).upper()
