"""
app.btcprotocol.hashing
==================
Cryptographic hash utilities used throughout the Bitcoin stack.

All functions operate on raw bytes.  No third-party libraries required;
everything is provided by the Python standard library (hashlib, hmac).

Public API
----------
sha256(data)                               -> bytes
double_sha256(data)                        -> bytes   Bitcoin "Hash256"
ripemd160(data)                            -> bytes
hash160(data)                              -> bytes   RIPEMD160(SHA256(data))
hmac_sha512(key, data)                     -> bytes
pbkdf2_hmac_sha512(pw, salt, iters)        -> bytes
tagged_hash(tag, data)                     -> bytes   BIP-340 tagged hash
merkle_root(hashes)                        -> bytes
merkle_proof(hashes, index)               -> list    Merkle proof path
verify_merkle_proof(leaf, proof, root, i) -> bool
checksum(data)                             -> bytes   first 4 bytes of double_sha256
compute_block_hash(header)                 -> str     little-endian hex
compute_txid(raw_tx)                       -> str
compute_wtxid(raw_tx)                      -> str
compute_target(bits)                       -> int     difficulty target from compact bits
difficulty_from_target(target)             -> float
work_from_target(target)                   -> int     estimated hash work
"""

import hashlib
import hmac as _hmac
import struct
from typing import List, Optional


# ---------------------------------------------------------------------------
# Basic digest wrappers
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> bytes:
    """Single SHA-256 digest."""
    return hashlib.sha256(data).digest()


def double_sha256(data: bytes) -> bytes:
    """SHA-256d: SHA-256(SHA-256(data)).  Used as Bitcoin's Hash256."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def ripemd160(data: bytes) -> bytes:
    """RIPEMD-160 digest.

    Uses hashlib.new('ripemd160') which is available in CPython on all
    platforms.  Falls back to a pure-Python implementation if the OpenSSL
    backend does not expose it (some stripped builds).
    """
    try:
        h = hashlib.new("ripemd160")
        h.update(data)
        return h.digest()
    except ValueError:
        return _ripemd160_pure(data)


def hash160(data: bytes) -> bytes:
    """RIPEMD160(SHA256(data)) — the standard Bitcoin public-key hash.

    Used to derive P2PKH and P2WPKH addresses from a compressed public key.
    """
    return ripemd160(sha256(data))


# ---------------------------------------------------------------------------
# HMAC / KDF
# ---------------------------------------------------------------------------

def hmac_sha512(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA-512.

    Used by BIP-32 child key derivation and BIP-39 seed generation.
    """
    return _hmac.new(key, data, hashlib.sha512).digest()


def pbkdf2_hmac_sha512(
    password: bytes,
    salt: bytes,
    iterations: int = 2048,
) -> bytes:
    """PBKDF2-HMAC-SHA512 with *iterations* rounds.

    Used by BIP-39 mnemonic_to_seed (2048 iterations by spec).
    Returns 64 bytes (512 bits).
    """
    return hashlib.pbkdf2_hmac(
        "sha512",
        password,
        salt,
        iterations,
        dklen=64,
    )


# ---------------------------------------------------------------------------
# BIP-340 tagged hash
# ---------------------------------------------------------------------------

# Cache of precomputed tag hashes so we don't recompute them on every call.
_TAGGED_HASH_CACHE: dict = {}


def tagged_hash(tag: str, data: bytes) -> bytes:
    """BIP-340 tagged hash: SHA256(SHA256(tag) || SHA256(tag) || data).

    Used in Taproot (BIP-341/342) and Schnorr signatures (BIP-340).

    The double prefix of the tag hash domain-separates the hash from
    other uses of SHA-256, preventing cross-protocol attacks.

    Parameters
    ----------
    tag:
        ASCII tag string, e.g. "BIP0340/challenge", "TapLeaf", "TapBranch".
    data:
        Payload bytes.

    Returns
    -------
    32-byte digest.
    """
    global _TAGGED_HASH_CACHE
    if tag not in _TAGGED_HASH_CACHE:
        tag_bytes = tag.encode("utf-8")
        _TAGGED_HASH_CACHE[tag] = sha256(tag_bytes)
    tag_hash = _TAGGED_HASH_CACHE[tag]
    return sha256(tag_hash + tag_hash + data)


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------

def merkle_root(hashes: List[bytes]) -> bytes:
    """Compute the Merkle root of a list of 32-byte transaction hashes.

    Follows Bitcoin's algorithm:
    - If the list has an odd number of entries, duplicate the last one.
    - Pairs are combined as double_sha256(a + b).
    - Recursion continues until one hash remains.

    Parameters
    ----------
    hashes:
        List of 32-byte hashes (txids in *internal* byte order).

    Returns
    -------
    32-byte Merkle root.  Returns 32 zero bytes for an empty list.
    """
    if not hashes:
        return b"\x00" * 32
    layer = list(hashes)
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        next_layer: List[bytes] = []
        for i in range(0, len(layer), 2):
            next_layer.append(double_sha256(layer[i] + layer[i + 1]))
        layer = next_layer
    return layer[0]


def merkle_proof(hashes: List[bytes], index: int) -> List[bytes]:
    """Generate a Merkle inclusion proof for the leaf at *index*.

    The proof is a list of sibling hashes from the leaf up to (but not
    including) the root.  To verify, combine the leaf with each sibling
    using the same pairing rule (left or right depends on the index bit).

    Parameters
    ----------
    hashes:
        Full list of leaf hashes.
    index:
        0-based index of the leaf for which the proof is generated.

    Returns
    -------
    List of sibling hashes (each 32 bytes).  An empty list means the tree
    has only one element (no siblings needed).

    Raises
    ------
    IndexError if *index* is out of range.
    """
    if not hashes:
        raise IndexError("merkle_proof: empty hash list")
    if index < 0 or index >= len(hashes):
        raise IndexError(
            f"merkle_proof: index {index} out of range for {len(hashes)} hashes"
        )

    proof: List[bytes] = []
    layer = list(hashes)
    current_index = index

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])

        # sibling index
        if current_index % 2 == 0:
            sibling_index = current_index + 1
        else:
            sibling_index = current_index - 1

        proof.append(layer[sibling_index])

        # Build next layer
        next_layer: List[bytes] = []
        for i in range(0, len(layer), 2):
            next_layer.append(double_sha256(layer[i] + layer[i + 1]))
        layer = next_layer
        current_index //= 2

    return proof


def verify_merkle_proof(
    leaf: bytes,
    proof: List[bytes],
    root: bytes,
    index: int,
) -> bool:
    """Verify a Merkle inclusion proof.

    Parameters
    ----------
    leaf:
        The 32-byte hash of the leaf to verify.
    proof:
        Sibling hashes as returned by :func:`merkle_proof`.
    root:
        The expected 32-byte Merkle root.
    index:
        0-based position of the leaf in the original list.

    Returns
    -------
    ``True`` if the proof is valid, ``False`` otherwise.
    """
    current = leaf
    current_index = index

    for sibling in proof:
        if current_index % 2 == 0:
            combined = current + sibling
        else:
            combined = sibling + current
        current = double_sha256(combined)
        current_index //= 2

    return current == root


# ---------------------------------------------------------------------------
# Bitcoin-specific helpers
# ---------------------------------------------------------------------------

def checksum(data: bytes) -> bytes:
    """Return the first 4 bytes of double_sha256(data).

    Used by Base58Check encoding.
    """
    return double_sha256(data)[:4]


def compute_txid(raw_tx: bytes) -> str:
    """Compute the (legacy) TXID of a serialised transaction.

    Returns the double-SHA256 hash reversed into display byte order (hex).
    This is the standard *big-endian* txid string shown in block explorers.
    """
    digest = double_sha256(raw_tx)
    return digest[::-1].hex()


def compute_wtxid(raw_tx: bytes) -> str:
    """Compute the witness TXID (wtxid) of a serialised SegWit transaction.

    The wtxid covers the full serialisation including witness data.
    The algorithm is identical to compute_txid; the caller is responsible
    for passing the correct (witness-inclusive) serialisation.
    """
    digest = double_sha256(raw_tx)
    return digest[::-1].hex()


def compute_block_hash(header: bytes) -> str:
    """Compute the display hash of an 80-byte block header.

    Returns the double-SHA256 of the header bytes reversed to big-endian
    hex — matching what explorers display as the block hash.

    Parameters
    ----------
    header:
        Exactly 80 bytes of serialised block header (version + prev_hash +
        merkle_root + time + bits + nonce).

    Raises
    ------
    ValueError if *header* is not 80 bytes.
    """
    if len(header) != 80:
        raise ValueError(
            f"compute_block_hash: expected 80-byte header, got {len(header)} bytes"
        )
    digest = double_sha256(header)
    return digest[::-1].hex()


def compute_target(bits: int) -> int:
    """Expand the compact-format *bits* field into a 256-bit integer target.

    The *bits* field encodes the proof-of-work target as a compact floating-
    point number: the top byte is the exponent (number of bytes) and the
    lower three bytes are the coefficient (mantissa).

    Formula: target = coefficient * 256^(exponent - 3)

    Parameters
    ----------
    bits:
        32-bit integer as stored in the block header (e.g. 0x1703a30c).

    Returns
    -------
    The full 256-bit integer target.
    """
    exponent = (bits >> 24) & 0xFF
    coefficient = bits & 0x007FFFFF
    # Handle the sign bit in the coefficient
    if bits & 0x00800000:
        coefficient = -(bits & 0x007FFFFF)
    target = coefficient * (256 ** (exponent - 3))
    return max(0, target)


def difficulty_from_target(target: int) -> float:
    """Compute the mining difficulty from a target value.

    Difficulty is defined relative to the genesis block target:
    difficulty = genesis_target / current_target

    The genesis target corresponds to bits = 0x1d00ffff.

    Parameters
    ----------
    target:
        Current 256-bit integer target (from :func:`compute_target`).

    Returns
    -------
    Difficulty as a float.  Returns 0.0 if target is zero.
    """
    if target == 0:
        return 0.0
    # Genesis block target: bits = 0x1d00ffff
    genesis_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
    return genesis_target / target


def work_from_target(target: int) -> int:
    """Estimate the expected number of hashes needed to meet *target*.

    Work is approximated as 2^256 / (target + 1).  This gives the expected
    number of SHA-256d operations needed before finding a valid block hash.

    Parameters
    ----------
    target:
        256-bit integer proof-of-work target.

    Returns
    -------
    Estimated hash work as a large integer.
    """
    if target < 0:
        return 0
    return (2 ** 256) // (target + 1)


# ---------------------------------------------------------------------------
# Pure-Python RIPEMD-160 fallback
# ---------------------------------------------------------------------------
# This implementation is based on the reference code from ripemd.org.
# It is only invoked when hashlib.new('ripemd160') raises ValueError,
# which happens on some OpenSSL builds with FIPS mode enabled.

def _ripemd160_pure(message: bytes) -> bytes:  # noqa: C901
    """Pure-Python RIPEMD-160.  Correct but slow; only a fallback."""

    KL = [0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
    KR = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000]

    RL = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
        3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12,
        1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
        4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13,
    ]
    RR = [
        5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12,
        6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
        15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13,
        8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
        12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11,
    ]
    SL = [
        11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8,
        7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
        11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5,
        11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
        9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6,
    ]
    SR = [
        8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6,
        9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
        9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5,
        15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
        8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11,
    ]

    def _f(j: int, x: int, y: int, z: int) -> int:
        if j < 16:
            return x ^ y ^ z
        elif j < 32:
            return (x & y) | (~x & z)
        elif j < 48:
            return (x | ~y) ^ z
        elif j < 64:
            return (x & z) | (y & ~z)
        else:
            return x ^ (y | ~z)

    def _rol(x: int, n: int) -> int:
        return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF

    msg = bytearray(message)
    orig_len = len(msg) * 8
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg += struct.pack("<Q", orig_len)

    h0, h1, h2, h3, h4 = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0

    for block_start in range(0, len(msg), 64):
        block = msg[block_start: block_start + 64]
        X = list(struct.unpack("<16I", block))

        al, bl, cl, dl, el = h0, h1, h2, h3, h4
        ar, br, cr, dr, er = h0, h1, h2, h3, h4

        for j in range(80):
            T = (
                _rol(
                    (al + _f(j, bl, cl, dl) + X[RL[j]] + KL[j // 16]) & 0xFFFFFFFF,
                    SL[j],
                )
                + el
            ) & 0xFFFFFFFF
            al, bl, cl, dl, el = el, T, bl, _rol(cl, 10), dl

            T = (
                _rol(
                    (ar + _f(79 - j, br, cr, dr) + X[RR[j]] + KR[j // 16]) & 0xFFFFFFFF,
                    SR[j],
                )
                + er
            ) & 0xFFFFFFFF
            ar, br, cr, dr, er = er, T, br, _rol(cr, 10), dr

        T = (h1 + cl + dr) & 0xFFFFFFFF
        h1 = (h2 + dl + er) & 0xFFFFFFFF
        h2 = (h3 + el + ar) & 0xFFFFFFFF
        h3 = (h4 + al + br) & 0xFFFFFFFF
        h4 = (h0 + bl + cr) & 0xFFFFFFFF
        h0 = T

    return struct.pack("<5I", h0, h1, h2, h3, h4)
