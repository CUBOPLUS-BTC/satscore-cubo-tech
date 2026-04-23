"""Bitcoin address validation and classification utilities.

All logic is pure-Python and standard-library only.  No third-party
cryptography libraries are required because we validate only the
structural / checksum properties of addresses.

Supported address types:
  - P2PKH   (legacy, starts with 1 on mainnet)
  - P2SH    (legacy script hash, starts with 3 on mainnet)
  - P2WPKH  (native segwit v0, starts with bc1q, 42 chars)
  - P2WSH   (native segwit v0 script hash, starts with bc1q, 62 chars)
  - P2TR    (taproot, starts with bc1p)
"""

import hashlib
import re
import struct

# ---------------------------------------------------------------------------
# Base58 alphabet and decode
# ---------------------------------------------------------------------------

_BASE58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_MAP = {c: i for i, c in enumerate(_BASE58_ALPHABET)}


def _base58_decode(address: str) -> bytes | None:
    """Decode a Base58Check address, returning raw bytes or None on error."""
    try:
        n = 0
        for char in address.encode():
            if char not in _BASE58_MAP:
                return None
            n = n * 58 + _BASE58_MAP[char]

        # Convert to bytes
        result = n.to_bytes((n.bit_length() + 7) // 8, "big") if n > 0 else b""

        # Preserve leading zero bytes (correspond to '1' characters)
        padding = len(address) - len(address.lstrip("1"))
        result = b"\x00" * padding + result

        return result
    except Exception:
        return None


def _check_base58_checksum(decoded: bytes) -> bool:
    """Return True if the last 4 bytes of *decoded* are a valid checksum."""
    if len(decoded) < 5:
        return False
    payload, checksum = decoded[:-4], decoded[-4:]
    digest = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    return digest[:4] == checksum


# ---------------------------------------------------------------------------
# Bech32 / Bech32m
# ---------------------------------------------------------------------------

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32M_CONST = 0x2BC830A3
_BECH32_CONST = 1


def _bech32_polymod(values: list[int]) -> int:
    """Compute the Bech32 polynomial checksum."""
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def decode_bech32(address: str) -> tuple[str | None, int | None, list[int] | None]:
    """Decode a Bech32 or Bech32m address.

    Parameters
    ----------
    address:
        The full bech32/bech32m address string.

    Returns
    -------
    tuple of (hrp, witness_version, witness_program)
    Returns (None, None, None) on any error.
    """
    address_lower = address.lower()
    if address_lower != address and address.upper() != address:
        return None, None, None  # mixed case

    address = address_lower
    pos = address.rfind("1")
    if pos < 1 or pos + 7 > len(address) or len(address) > 90:
        return None, None, None

    hrp = address[:pos]
    data_chars = address[pos + 1:]

    for c in data_chars:
        if c not in _BECH32_CHARSET:
            return None, None, None

    data = [_BECH32_CHARSET.find(c) for c in data_chars]
    const = _bech32_polymod(_bech32_hrp_expand(hrp) + data)

    if const not in (_BECH32_CONST, _BECH32M_CONST):
        return None, None, None

    # First data byte is the witness version
    witness_version = data[0]
    if witness_version > 16:
        return None, None, None

    # Convert 5-bit groups to 8-bit
    decoded = data[1:-6]
    bits = 0
    val = 0
    result = []
    for d in decoded:
        val = (val << 5) | d
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((val >> bits) & 0xFF)

    if bits >= 5 or val & ((1 << bits) - 1):
        return None, None, None

    return hrp, witness_version, result


# ---------------------------------------------------------------------------
# Address type classification
# ---------------------------------------------------------------------------

def get_address_type(address: str) -> str:
    """Classify a Bitcoin address by its structural type.

    Returns one of:
        "p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr", "unknown"
    """
    if not address or not isinstance(address, str):
        return "unknown"

    addr = address.strip()

    # Bech32 / bech32m (segwit)
    if addr.lower().startswith(("bc1", "tb1", "bcrt1")):
        hrp, witness_version, program = decode_bech32(addr)
        if program is None:
            return "unknown"
        if witness_version == 0:
            if len(program) == 20:
                return "p2wpkh"
            if len(program) == 32:
                return "p2wsh"
        if witness_version == 1 and len(program) == 32:
            return "p2tr"
        return "unknown"

    # Base58Check
    decoded = _base58_decode(addr)
    if decoded is None or len(decoded) != 25:
        return "unknown"
    if not _check_base58_checksum(decoded):
        return "unknown"

    version_byte = decoded[0]
    # Mainnet P2PKH: 0x00  Testnet P2PKH: 0x6F
    if version_byte in (0x00, 0x6F):
        return "p2pkh"
    # Mainnet P2SH: 0x05  Testnet P2SH: 0xC4
    if version_byte in (0x05, 0xC4):
        return "p2sh"

    return "unknown"


# ---------------------------------------------------------------------------
# Network detection
# ---------------------------------------------------------------------------

def is_mainnet(address: str) -> bool:
    """Return True if *address* is a mainnet Bitcoin address."""
    addr = address.strip()
    if addr.lower().startswith("bc1"):
        return True
    decoded = _base58_decode(addr)
    if decoded and len(decoded) == 25 and _check_base58_checksum(decoded):
        return decoded[0] in (0x00, 0x05)
    return False


def is_testnet(address: str) -> bool:
    """Return True if *address* is a testnet or regtest Bitcoin address."""
    addr = address.strip()
    if addr.lower().startswith(("tb1", "bcrt1")):
        return True
    decoded = _base58_decode(addr)
    if decoded and len(decoded) == 25 and _check_base58_checksum(decoded):
        return decoded[0] in (0x6F, 0xC4)
    return False


# ---------------------------------------------------------------------------
# Full validation
# ---------------------------------------------------------------------------

def validate_address(address: str) -> dict:
    """Validate and classify a Bitcoin address.

    Parameters
    ----------
    address:
        The address string to validate.

    Returns
    -------
    dict with keys:
        valid (bool), address_type (str), network (str),
        is_segwit (bool), is_taproot (bool),
        estimated_input_vbytes (int), detail (str)
    """
    if not address or not isinstance(address, str):
        return {
            "valid": False,
            "address_type": "unknown",
            "network": "unknown",
            "is_segwit": False,
            "is_taproot": False,
            "estimated_input_vbytes": 0,
            "detail": "Address must be a non-empty string",
        }

    addr = address.strip()
    addr_type = get_address_type(addr)

    if addr_type == "unknown":
        return {
            "valid": False,
            "address_type": "unknown",
            "network": "unknown",
            "is_segwit": False,
            "is_taproot": False,
            "estimated_input_vbytes": 0,
            "detail": "Unrecognised address format or invalid checksum",
        }

    network = "mainnet" if is_mainnet(addr) else ("testnet" if is_testnet(addr) else "unknown")
    is_segwit = addr_type in ("p2wpkh", "p2wsh", "p2tr")
    is_taproot = addr_type == "p2tr"
    input_vbytes = estimate_address_size(addr_type)

    type_descriptions = {
        "p2pkh": "Pay-to-Public-Key-Hash (Legacy)",
        "p2sh": "Pay-to-Script-Hash (Legacy/SegWit-wrapped)",
        "p2wpkh": "Pay-to-Witness-Public-Key-Hash (Native SegWit v0)",
        "p2wsh": "Pay-to-Witness-Script-Hash (Native SegWit v0 multisig)",
        "p2tr": "Pay-to-Taproot (SegWit v1)",
    }

    return {
        "valid": True,
        "address": addr,
        "address_type": addr_type,
        "address_type_name": type_descriptions.get(addr_type, addr_type),
        "network": network,
        "is_segwit": is_segwit,
        "is_taproot": is_taproot,
        "estimated_input_vbytes": input_vbytes,
        "detail": "Valid address",
    }


# ---------------------------------------------------------------------------
# Size estimation
# ---------------------------------------------------------------------------

# vbyte sizes for spending a UTXO of each address type (input side)
_INPUT_VBYTES = {
    "p2pkh":  148,  # 41 scriptSig + 107 sig+pubkey + overhead
    "p2sh":   91,   # approximate (varies by redeem script)
    "p2wpkh": 68,   # 41 non-witness + 27 witness scaled
    "p2wsh":  105,  # approximate (varies by witness script)
    "p2tr":   57,   # keypath spend
}

# vbyte sizes for a script pubkey output of each type
_OUTPUT_VBYTES = {
    "p2pkh":  34,
    "p2sh":   32,
    "p2wpkh": 31,
    "p2wsh":  43,
    "p2tr":   43,
}


def estimate_address_size(address_type: str) -> int:
    """Return the estimated input size in vbytes for a given address type.

    Parameters
    ----------
    address_type:
        One of "p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr".

    Returns
    -------
    int  — vbytes.  Returns 0 for unknown types.
    """
    return _INPUT_VBYTES.get(address_type, 0)


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------

def compare_address_types() -> list:
    """Return a comparison table of all supported Bitcoin address types.

    Returns
    -------
    list of dict, one per address type, with keys:
        type, name, network_prefix, input_vbytes, output_vbytes,
        is_segwit, is_taproot, recommended, notes
    """
    return [
        {
            "type": "p2pkh",
            "name": "Legacy",
            "network_prefix": "1 (mainnet) / m or n (testnet)",
            "input_vbytes": _INPUT_VBYTES["p2pkh"],
            "output_vbytes": _OUTPUT_VBYTES["p2pkh"],
            "is_segwit": False,
            "is_taproot": False,
            "recommended": False,
            "notes": "Highest fees; maximum compatibility with very old software.",
        },
        {
            "type": "p2sh",
            "name": "Pay-to-Script-Hash",
            "network_prefix": "3 (mainnet) / 2 (testnet)",
            "input_vbytes": _INPUT_VBYTES["p2sh"],
            "output_vbytes": _OUTPUT_VBYTES["p2sh"],
            "is_segwit": False,
            "is_taproot": False,
            "recommended": False,
            "notes": "Used for wrapped SegWit (P2SH-P2WPKH) and multisig scripts.",
        },
        {
            "type": "p2wpkh",
            "name": "Native SegWit v0",
            "network_prefix": "bc1q (mainnet, 42 chars) / tb1q (testnet)",
            "input_vbytes": _INPUT_VBYTES["p2wpkh"],
            "output_vbytes": _OUTPUT_VBYTES["p2wpkh"],
            "is_segwit": True,
            "is_taproot": False,
            "recommended": True,
            "notes": "~40% cheaper than P2PKH; wide wallet support.",
        },
        {
            "type": "p2wsh",
            "name": "Native SegWit v0 Script Hash",
            "network_prefix": "bc1q (mainnet, 62 chars)",
            "input_vbytes": _INPUT_VBYTES["p2wsh"],
            "output_vbytes": _OUTPUT_VBYTES["p2wsh"],
            "is_segwit": True,
            "is_taproot": False,
            "recommended": False,
            "notes": "Used for native SegWit multisig and complex scripts.",
        },
        {
            "type": "p2tr",
            "name": "Taproot",
            "network_prefix": "bc1p (mainnet) / tb1p (testnet)",
            "input_vbytes": _INPUT_VBYTES["p2tr"],
            "output_vbytes": _OUTPUT_VBYTES["p2tr"],
            "is_segwit": True,
            "is_taproot": True,
            "recommended": True,
            "notes": "Cheapest keypath spend; enhanced privacy; Schnorr signatures.",
        },
    ]
