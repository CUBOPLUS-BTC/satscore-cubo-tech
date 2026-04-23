"""
app.btcprotocol.encoding
===================
Encoding / decoding utilities used by the Bitcoin protocol.

All functions use only the Python standard library.

Public API
----------
base58_alphabet                           - constant (str)
base58_encode(data)                       -> str
base58_decode(s)                          -> bytes
base58check_encode(version, payload)      -> str
base58check_decode(s)                     -> (version: int, payload: bytes)
bech32_charset                            - constant (str)
bech32_polymod(values)                    -> int
bech32_hrp_expand(hrp)                    -> list
bech32_encode(hrp, data)                  -> str   (raw 5-bit list)
bech32_decode(addr)                       -> (hrp: str, data: list)
bech32m_encode(hrp, data)                 -> str
bech32m_decode(addr)                      -> (hrp: str, data: list)
convertbits(data, frombits, tobits, pad)  -> list
segwit_addr_encode(hrp, witver, witprog)  -> str
segwit_addr_decode(hrp, addr)             -> (witver: int, witprog: list)
compact_size_encode(n)                    -> bytes
compact_size_decode(data, offset)         -> (value, new_offset)
int_to_little_endian(n, length)           -> bytes
little_endian_to_int(b)                   -> int
int_to_big_endian(n, length)              -> bytes
big_endian_to_int(b)                      -> int
der_encode_integer(value)                 -> bytes
der_encode_signature(r, s)                -> bytes  (full DER SEQUENCE)
der_decode_signature(der)                 -> (r, s)
hex_to_bytes(s)                           -> bytes
bytes_to_hex(b)                           -> str
reverse_bytes(b)                          -> bytes
"""

from .hashing import double_sha256

# ---------------------------------------------------------------------------
# Base-58 alphabet
# ---------------------------------------------------------------------------

base58_alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

_B58_ALPHABET_BYTES = base58_alphabet.encode("ascii")
_B58_MAP = {c: i for i, c in enumerate(_B58_ALPHABET_BYTES)}


def base58_encode(data: bytes) -> str:
    """Encode *data* using the Bitcoin Base58 alphabet (no checksum).

    Leading zero bytes are preserved as leading '1' characters.
    """
    count = 0
    for byte in data:
        if byte == 0:
            count += 1
        else:
            break

    n = int.from_bytes(data, "big")
    result = []
    while n:
        n, rem = divmod(n, 58)
        result.append(_B58_ALPHABET_BYTES[rem])

    result.extend([_B58_ALPHABET_BYTES[0]] * count)
    return bytes(reversed(result)).decode("ascii")


def base58_decode(s: str) -> bytes:
    """Decode a Base58-encoded string (no checksum verification).

    Raises
    ------
    ValueError on characters outside the Base58 alphabet.
    """
    count = 0
    for c in s:
        if c == "1":
            count += 1
        else:
            break

    n = 0
    for c in s:
        byte_val = ord(c)
        if byte_val not in _B58_MAP:
            raise ValueError(
                f"base58_decode: invalid character '{c}' (ord={byte_val})"
            )
        n = n * 58 + _B58_MAP[byte_val]

    result = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * count + result


def base58check_encode(version: int, payload: bytes) -> str:
    """Base58Check: encode version byte + payload with 4-byte checksum.

    Parameters
    ----------
    version:
        Single version byte (0-255).  For mainnet P2PKH it is 0x00,
        for mainnet P2SH it is 0x05, for WIF it is 0x80.
    payload:
        Raw payload bytes (e.g. 20-byte public key hash).

    Returns
    -------
    Base58Check-encoded string.
    """
    if not 0 <= version <= 255:
        raise ValueError(
            f"base58check_encode: version must be 0-255, got {version}"
        )
    data = bytes([version]) + payload
    chk = double_sha256(data)[:4]
    return base58_encode(data + chk)


def base58check_decode(s: str) -> tuple:
    """Decode a Base58Check string.

    Returns
    -------
    (version: int, payload: bytes)

    Raises
    ------
    ValueError if the checksum does not match or the string is malformed.
    """
    raw = base58_decode(s)
    if len(raw) < 5:
        raise ValueError(
            f"base58check_decode: string too short (need >=5 decoded bytes, got {len(raw)})"
        )
    version = raw[0]
    payload = raw[1:-4]
    chk = raw[-4:]
    expected = double_sha256(raw[:-4])[:4]
    if chk != expected:
        raise ValueError(
            f"Base58Check checksum mismatch: got {chk.hex()}, expected {expected.hex()}"
        )
    return version, payload


# ---------------------------------------------------------------------------
# Bech32 / Bech32m (BIP-173 / BIP-350)
# ---------------------------------------------------------------------------

bech32_charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

_BECH32_CHARSET_MAP = {c: i for i, c in enumerate(bech32_charset)}

_BECH32_CONST = 1            # BIP-173 checksum constant
_BECH32M_CONST = 0x2BC830A3  # BIP-350 checksum constant


def bech32_polymod(values: list) -> int:
    """Compute the Bech32 BCH checksum over *values* (list of 5-bit ints).

    Returns the final checksum register value.  A valid encoding has
    polymod == 1 (Bech32) or == 0x2BC830A3 (Bech32m).
    """
    GEN = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def bech32_hrp_expand(hrp: str) -> list:
    """Expand the human-readable part for checksum computation.

    Returns a list: [high bits of each char] + [0] + [low bits of each char].
    """
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_create_checksum(hrp: str, data: list, const: int) -> list:
    """Create a 6-element checksum for the given HRP, data, and encoding constant."""
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ const
    return [(polymod >> (5 * (5 - i))) & 31 for i in range(6)]


def bech32_encode(hrp: str, data: list) -> str:
    """Encode a Bech32 string from HRP and 5-bit data values.

    Uses the Bech32 (BIP-173) checksum constant.  For witness v0 addresses.

    Parameters
    ----------
    hrp:
        Human-readable part, e.g. "bc", "tb", "bcrt".
    data:
        List of 5-bit integer values (the payload, without checksum).

    Returns
    -------
    Lowercase Bech32 string.
    """
    combined = data + _bech32_create_checksum(hrp, data, _BECH32_CONST)
    return hrp + "1" + "".join(bech32_charset[d] for d in combined)


def bech32_decode(addr: str) -> tuple:
    """Decode a Bech32 string.

    Returns
    -------
    (hrp: str, data: list)  where data is the 5-bit payload (without checksum).

    Raises
    ------
    ValueError on invalid encoding, wrong checksum, or mixed case.
    """
    return _bech32_decode_raw(addr, expected_const=_BECH32_CONST)


def bech32m_encode(hrp: str, data: list) -> str:
    """Encode a Bech32m string (BIP-350) for witness v1+ addresses.

    Parameters
    ----------
    hrp:
        Human-readable part, e.g. "bc", "tb".
    data:
        List of 5-bit integer values.

    Returns
    -------
    Lowercase Bech32m string.
    """
    combined = data + _bech32_create_checksum(hrp, data, _BECH32M_CONST)
    return hrp + "1" + "".join(bech32_charset[d] for d in combined)


def bech32m_decode(addr: str) -> tuple:
    """Decode a Bech32m string (BIP-350).

    Returns
    -------
    (hrp: str, data: list)

    Raises
    ------
    ValueError on invalid encoding or wrong checksum constant.
    """
    return _bech32_decode_raw(addr, expected_const=_BECH32M_CONST)


def _bech32_decode_raw(addr: str, expected_const: int) -> tuple:
    """Internal: decode either Bech32 or Bech32m, enforcing the given constant."""
    # Mixed-case check
    if addr.lower() != addr and addr.upper() != addr:
        raise ValueError("bech32: mixed-case address is not valid")
    addr = addr.lower()

    pos = addr.rfind("1")
    if pos < 1 or pos + 7 > len(addr) or len(addr) > 90:
        raise ValueError(
            f"bech32: invalid structure (separator pos={pos}, len={len(addr)})"
        )

    hrp = addr[:pos]
    data_str = addr[pos + 1:]

    for c in data_str:
        if c not in _BECH32_CHARSET_MAP:
            raise ValueError(f"bech32: invalid character '{c}' in data part")

    decoded = [_BECH32_CHARSET_MAP[c] for c in data_str]
    const = bech32_polymod(bech32_hrp_expand(hrp) + decoded)
    if const != expected_const:
        raise ValueError(
            f"bech32: checksum mismatch (got const=0x{const:08X}, "
            f"expected 0x{expected_const:08X})"
        )

    return hrp, decoded[:-6]


def convertbits(data, frombits: int, tobits: int, pad: bool = True) -> list:
    """General power-of-2 base conversion.

    Converts a sequence of integers in base ``2**frombits`` to a list of
    integers in base ``2**tobits``.  Used to convert between 8-bit bytes
    and 5-bit Bech32 groups.

    Parameters
    ----------
    data:
        Iterable of integers (each in range 0 .. 2**frombits - 1).
    frombits:
        Source bit width (e.g. 8).
    tobits:
        Destination bit width (e.g. 5).
    pad:
        If True, pad the final group with zero bits.  If False, verify
        no non-zero padding bits are present (for decoding).

    Returns
    -------
    List of integers, or an empty list if padding error detected (pad=False).
    """
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return []
        acc = ((acc << frombits) | value) & max_acc
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


def segwit_addr_encode(hrp: str, witver: int, witprog: bytes) -> str:
    """Encode a native SegWit address.

    Parameters
    ----------
    hrp:
        Network HRP: "bc" (mainnet), "tb" (testnet), "bcrt" (regtest).
    witver:
        Witness version (0 for P2WPKH/P2WSH, 1 for P2TR).
    witprog:
        Witness program bytes (20 bytes for v0 P2WPKH, 32 bytes for v0 P2WSH
        or v1 P2TR).

    Returns
    -------
    Lowercase SegWit address string.

    Raises
    ------
    ValueError on invalid inputs.
    """
    if witver < 0 or witver > 16:
        raise ValueError(f"segwit_addr_encode: witness version must be 0-16, got {witver}")
    if witver == 0 and len(witprog) not in (20, 32):
        raise ValueError(
            f"segwit_addr_encode: v0 witness program must be 20 or 32 bytes, "
            f"got {len(witprog)}"
        )
    if witver >= 1 and not (2 <= len(witprog) <= 40):
        raise ValueError(
            f"segwit_addr_encode: v1+ witness program must be 2-40 bytes"
        )

    data = [witver] + convertbits(witprog, 8, 5)
    const = _BECH32_CONST if witver == 0 else _BECH32M_CONST
    combined = data + _bech32_create_checksum(hrp, data, const)
    return hrp + "1" + "".join(bech32_charset[d] for d in combined)


def segwit_addr_decode(hrp: str, addr: str) -> tuple:
    """Decode a native SegWit address.

    Parameters
    ----------
    hrp:
        Expected network HRP (e.g. "bc").
    addr:
        SegWit address string.

    Returns
    -------
    (witver: int, witprog: list)  where witprog is a list of integers (bytes).

    Raises
    ------
    ValueError on invalid address, wrong HRP, wrong checksum constant, or
    invalid witness program length.
    """
    addr_lower = addr.lower()
    if addr_lower.lower() != addr.lower():
        raise ValueError("segwit_addr_decode: mixed-case address")

    pos = addr_lower.rfind("1")
    if pos < 1 or pos + 7 > len(addr_lower) or len(addr_lower) > 90:
        raise ValueError("segwit_addr_decode: invalid address structure")

    addr_hrp = addr_lower[:pos]
    if addr_hrp != hrp.lower():
        raise ValueError(
            f"segwit_addr_decode: HRP mismatch: expected '{hrp}', got '{addr_hrp}'"
        )

    data_str = addr_lower[pos + 1:]
    for c in data_str:
        if c not in _BECH32_CHARSET_MAP:
            raise ValueError(f"segwit_addr_decode: invalid character '{c}'")

    decoded = [_BECH32_CHARSET_MAP[c] for c in data_str]

    if not decoded:
        raise ValueError("segwit_addr_decode: empty data part")

    witver = decoded[0]
    if witver > 16:
        raise ValueError(f"segwit_addr_decode: invalid witness version {witver}")

    expected_const = _BECH32_CONST if witver == 0 else _BECH32M_CONST
    const = bech32_polymod(bech32_hrp_expand(addr_hrp) + decoded)
    if const != expected_const:
        raise ValueError("segwit_addr_decode: invalid checksum")

    payload_5bit = decoded[1:-6]
    witprog = convertbits(payload_5bit, 5, 8, pad=False)
    if not witprog:
        raise ValueError("segwit_addr_decode: bit-conversion failure")

    if witver == 0 and len(witprog) not in (20, 32):
        raise ValueError(
            f"segwit_addr_decode: v0 program must be 20 or 32 bytes, got {len(witprog)}"
        )
    if not (2 <= len(witprog) <= 40):
        raise ValueError(
            f"segwit_addr_decode: witness program length out of range: {len(witprog)}"
        )

    return witver, witprog


# ---------------------------------------------------------------------------
# Bitcoin CompactSize (varint)
# ---------------------------------------------------------------------------

def compact_size_encode(n: int) -> bytes:
    """Encode an integer as a Bitcoin CompactSize (variable-length integer).

    Encoding rules:
    - 0x00..0xFC         → 1 byte
    - 0xFD..0xFFFF       → 0xFD + 2-byte LE
    - 0x10000..0xFFFFFFFF → 0xFE + 4-byte LE
    - larger             → 0xFF + 8-byte LE

    Raises
    ------
    ValueError if *n* is negative.
    OverflowError if *n* exceeds 2^64 - 1.
    """
    if n < 0:
        raise ValueError(f"compact_size_encode: n must be non-negative, got {n}")
    if n > 0xFFFFFFFFFFFFFFFF:
        raise OverflowError(f"compact_size_encode: n={n} exceeds maximum CompactSize value")
    if n < 0xFD:
        return bytes([n])
    elif n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    elif n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    else:
        return b"\xff" + n.to_bytes(8, "little")


def compact_size_decode(data: bytes, offset: int = 0) -> tuple:
    """Read a CompactSize integer from *data* at *offset*.

    Returns
    -------
    (value: int, new_offset: int)

    Raises
    ------
    ValueError on buffer underflow or invalid offset.
    """
    if offset < 0 or offset >= len(data):
        raise ValueError(
            f"compact_size_decode: offset {offset} out of range for buffer len {len(data)}"
        )

    first = data[offset]
    if first < 0xFD:
        return first, offset + 1
    elif first == 0xFD:
        if offset + 3 > len(data):
            raise ValueError("compact_size_decode: buffer too short for 2-byte varint")
        return int.from_bytes(data[offset + 1: offset + 3], "little"), offset + 3
    elif first == 0xFE:
        if offset + 5 > len(data):
            raise ValueError("compact_size_decode: buffer too short for 4-byte varint")
        return int.from_bytes(data[offset + 1: offset + 5], "little"), offset + 5
    else:  # 0xFF
        if offset + 9 > len(data):
            raise ValueError("compact_size_decode: buffer too short for 8-byte varint")
        return int.from_bytes(data[offset + 1: offset + 9], "little"), offset + 9


# ---------------------------------------------------------------------------
# Integer ↔ bytes helpers
# ---------------------------------------------------------------------------

def int_to_little_endian(n: int, length: int) -> bytes:
    """Encode *n* as a little-endian integer of exactly *length* bytes.

    Raises
    ------
    ValueError if *n* is negative or does not fit in *length* bytes.
    """
    if n < 0:
        raise ValueError(f"int_to_little_endian: n must be non-negative, got {n}")
    return n.to_bytes(length, "little")


def little_endian_to_int(b: bytes) -> int:
    """Decode a little-endian byte sequence to an integer."""
    return int.from_bytes(b, "little")


def int_to_big_endian(n: int, length: int) -> bytes:
    """Encode *n* as a big-endian integer of exactly *length* bytes.

    Raises
    ------
    ValueError if *n* is negative or does not fit in *length* bytes.
    """
    if n < 0:
        raise ValueError(f"int_to_big_endian: n must be non-negative, got {n}")
    return n.to_bytes(length, "big")


def big_endian_to_int(b: bytes) -> int:
    """Decode a big-endian byte sequence to an integer."""
    return int.from_bytes(b, "big")


# ---------------------------------------------------------------------------
# DER encoding
# ---------------------------------------------------------------------------

def der_encode_integer(value: int) -> bytes:
    """Encode a non-negative integer as a DER INTEGER element (tag 0x02).

    A 0x00 padding byte is prepended when the most-significant bit is set
    to prevent interpretation as a negative number.

    Returns
    -------
    Bytes: 0x02 + length + value_bytes
    """
    if value < 0:
        raise ValueError("der_encode_integer: only non-negative integers supported")
    if value == 0:
        return b"\x02\x01\x00"
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    if raw[0] & 0x80:
        raw = b"\x00" + raw
    return bytes([0x02, len(raw)]) + raw


def der_encode_signature(r: int, s: int) -> bytes:
    """Encode an ECDSA (r, s) pair as a DER SEQUENCE.

    Bitcoin requires low-S signatures (BIP-62), but this function does NOT
    enforce that — the caller is responsible.

    DER structure: 0x30 len(0x02 len_r r 0x02 len_s s)
    """
    r_enc = der_encode_integer(r)
    s_enc = der_encode_integer(s)
    payload = r_enc + s_enc
    return bytes([0x30, len(payload)]) + payload


def der_decode_signature(der: bytes) -> tuple:
    """Decode a DER-encoded ECDSA signature into (r, s).

    Returns
    -------
    (r: int, s: int)

    Raises
    ------
    ValueError on malformed input.
    """
    if len(der) < 8:
        raise ValueError("der_decode_signature: data too short")
    if der[0] != 0x30:
        raise ValueError(
            f"der_decode_signature: expected SEQUENCE tag 0x30, got 0x{der[0]:02X}"
        )
    seq_len = der[1]
    if seq_len + 2 > len(der):
        raise ValueError("der_decode_signature: sequence length exceeds buffer")

    offset = 2

    def _read_int(off: int) -> tuple:
        if off >= len(der):
            raise ValueError("der_decode_signature: unexpected end of buffer")
        if der[off] != 0x02:
            raise ValueError(
                f"der_decode_signature: expected INTEGER tag 0x02 at offset {off}, "
                f"got 0x{der[off]:02X}"
            )
        length = der[off + 1]
        raw = der[off + 2: off + 2 + length]
        if len(raw) != length:
            raise ValueError("der_decode_signature: truncated integer")
        value = int.from_bytes(raw, "big")
        return value, off + 2 + length

    r, offset = _read_int(offset)
    s, _ = _read_int(offset)
    return r, s


# ---------------------------------------------------------------------------
# Hex helpers
# ---------------------------------------------------------------------------

def hex_to_bytes(s: str) -> bytes:
    """Convert a hex string (with or without 0x prefix) to bytes.

    Odd-length strings are left-padded with a zero nibble.
    """
    s = s.strip()
    if s.startswith(("0x", "0X")):
        s = s[2:]
    if len(s) % 2:
        s = "0" + s
    return bytes.fromhex(s)


def bytes_to_hex(b: bytes) -> str:
    """Convert bytes to lowercase hex string (no 0x prefix)."""
    return b.hex()


def reverse_bytes(b: bytes) -> bytes:
    """Reverse the byte order (little-endian ↔ big-endian conversion).

    Commonly used to convert between internal byte order and display byte
    order for transaction IDs and block hashes.
    """
    return b[::-1]


# ---------------------------------------------------------------------------
# Backward-compatible aliases (used by older call sites in this codebase)
# ---------------------------------------------------------------------------

# compact_size / read_compact_size kept as aliases for compatibility
compact_size = compact_size_encode
read_compact_size = compact_size_decode
