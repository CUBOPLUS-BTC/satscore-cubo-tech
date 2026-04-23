"""
app.btcprotocol.script
=================
Bitcoin Script system — educational reference implementation.

All Bitcoin opcodes are defined as integer constants.  The Script class
parses raw script bytes and classifies them into standard script types
(P2PKH, P2SH, P2WPKH, P2WSH, P2TR, multisig, OP_RETURN, unknown).

No private keys or signatures are generated here; this module is purely
for understanding and inspecting Bitcoin script structures.

Public API
----------
Opcode constants   OP_0, OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG ...
OPCODE_NAMES       {byte_value: name_str}
OPCODE_VALUES      {name_str: byte_value}
Script             - parse, classify, disassemble, is_standard, is_witness
ScriptBuilder      - fluent builder for script construction
build_p2pkh_script(pubkey_hash)    -> Script
build_p2sh_script(script_hash)     -> Script
build_p2wpkh_script(pubkey_hash)   -> Script
build_p2wsh_script(script_hash)    -> Script
build_p2tr_script(tweaked_pubkey)  -> Script
build_multisig_script(m, pubkeys)  -> Script
build_op_return_script(data)       -> Script
build_timelock_script(locktime, pubkey_hash) -> Script
"""

from __future__ import annotations
from typing import List, Optional, Union

# ---------------------------------------------------------------------------
# Opcode constants
# ---------------------------------------------------------------------------

# Constants / push opcodes
OP_0              = 0x00  # OP_FALSE: push empty byte array
OP_PUSHDATA1      = 0x4C  # next byte = length; push that many bytes
OP_PUSHDATA2      = 0x4D  # next 2 bytes (LE) = length; push that many bytes
OP_PUSHDATA4      = 0x4E  # next 4 bytes (LE) = length; push that many bytes
OP_1NEGATE        = 0x4F  # push -1
OP_RESERVED       = 0x50
OP_1              = 0x51  # OP_TRUE: push 1
OP_2              = 0x52
OP_3              = 0x53
OP_4              = 0x54
OP_5              = 0x55
OP_6              = 0x56
OP_7              = 0x57
OP_8              = 0x58
OP_9              = 0x59
OP_10             = 0x5A
OP_11             = 0x5B
OP_12             = 0x5C
OP_13             = 0x5D
OP_14             = 0x5E
OP_15             = 0x5F
OP_16             = 0x60

# Aliases
OP_FALSE = OP_0
OP_TRUE  = OP_1

# Flow control
OP_NOP            = 0x61
OP_VER            = 0x62
OP_IF             = 0x63
OP_NOTIF          = 0x64
OP_VERIF          = 0x65
OP_VERNOTIF       = 0x66
OP_ELSE           = 0x67
OP_ENDIF          = 0x68
OP_VERIFY         = 0x69
OP_RETURN         = 0x6A

# Stack
OP_TOALTSTACK     = 0x6B
OP_FROMALTSTACK   = 0x6C
OP_IFDUP          = 0x73
OP_DEPTH          = 0x74
OP_DROP           = 0x75
OP_DUP            = 0x76
OP_NIP            = 0x77
OP_OVER           = 0x78
OP_PICK           = 0x79
OP_ROLL           = 0x7A
OP_ROT            = 0x7B
OP_SWAP           = 0x7C
OP_TUCK           = 0x7D
OP_2DROP          = 0x6D
OP_2DUP           = 0x6E
OP_3DUP           = 0x6F
OP_2OVER          = 0x70
OP_2ROT           = 0x71
OP_2SWAP          = 0x72

# Splice
OP_CAT            = 0x7E  # (disabled)
OP_SUBSTR         = 0x7F  # (disabled)
OP_LEFT           = 0x80  # (disabled)
OP_RIGHT          = 0x81  # (disabled)
OP_SIZE           = 0x82

# Bitwise logic
OP_INVERT         = 0x83  # (disabled)
OP_AND            = 0x84  # (disabled)
OP_OR             = 0x85  # (disabled)
OP_XOR            = 0x86  # (disabled)
OP_EQUAL          = 0x87
OP_EQUALVERIFY    = 0x88
OP_RESERVED1      = 0x89
OP_RESERVED2      = 0x8A

# Arithmetic
OP_1ADD           = 0x8B
OP_1SUB           = 0x8C
OP_2MUL           = 0x8D  # (disabled)
OP_2DIV           = 0x8E  # (disabled)
OP_NEGATE         = 0x8F
OP_ABS            = 0x90
OP_NOT            = 0x91
OP_0NOTEQUAL      = 0x92
OP_ADD            = 0x93
OP_SUB            = 0x94
OP_MUL            = 0x95  # (disabled)
OP_DIV            = 0x96  # (disabled)
OP_MOD            = 0x97  # (disabled)
OP_LSHIFT         = 0x98  # (disabled)
OP_RSHIFT         = 0x99  # (disabled)
OP_BOOLAND        = 0x9A
OP_BOOLOR         = 0x9B
OP_NUMEQUAL       = 0x9C
OP_NUMEQUALVERIFY = 0x9D
OP_NUMNOTEQUAL    = 0x9E
OP_LESSTHAN       = 0x9F
OP_GREATERTHAN    = 0xA0
OP_LESSTHANOREQUAL    = 0xA1
OP_GREATERTHANOREQUAL = 0xA2
OP_MIN            = 0xA3
OP_MAX            = 0xA4
OP_WITHIN         = 0xA5

# Hashing
OP_RIPEMD160      = 0xA6
OP_SHA1           = 0xA7
OP_SHA256         = 0xA8
OP_HASH160        = 0xA9
OP_HASH256        = 0xAA
OP_CODESEPARATOR  = 0xAB
OP_CHECKSIG       = 0xAC
OP_CHECKSIGVERIFY = 0xAD
OP_CHECKMULTISIG  = 0xAE
OP_CHECKMULTISIGVERIFY = 0xAF

# Tapscript (BIP-342)
OP_CHECKSIGADD    = 0xBA

# Locktime
OP_CHECKLOCKTIMEVERIFY = 0xB1  # OP_CLTV (BIP-65)
OP_CHECKSEQUENCEVERIFY = 0xB2  # OP_CSV  (BIP-112)

# NOP extensions
OP_NOP1           = 0xB0
OP_NOP4           = 0xB3
OP_NOP5           = 0xB4
OP_NOP6           = 0xB5
OP_NOP7           = 0xB6
OP_NOP8           = 0xB7
OP_NOP9           = 0xB8
OP_NOP10          = 0xB9

# Pseudo-opcodes (not valid in script; used in implementation)
OP_PUBKEYHASH     = 0xFD
OP_PUBKEY         = 0xFE
OP_INVALIDOPCODE  = 0xFF

# ---------------------------------------------------------------------------
# Opcode name maps
# ---------------------------------------------------------------------------

OPCODE_NAMES: dict = {
    0x00: "OP_0",
    0x4C: "OP_PUSHDATA1",
    0x4D: "OP_PUSHDATA2",
    0x4E: "OP_PUSHDATA4",
    0x4F: "OP_1NEGATE",
    0x50: "OP_RESERVED",
    0x51: "OP_1",
    0x52: "OP_2",
    0x53: "OP_3",
    0x54: "OP_4",
    0x55: "OP_5",
    0x56: "OP_6",
    0x57: "OP_7",
    0x58: "OP_8",
    0x59: "OP_9",
    0x5A: "OP_10",
    0x5B: "OP_11",
    0x5C: "OP_12",
    0x5D: "OP_13",
    0x5E: "OP_14",
    0x5F: "OP_15",
    0x60: "OP_16",
    0x61: "OP_NOP",
    0x62: "OP_VER",
    0x63: "OP_IF",
    0x64: "OP_NOTIF",
    0x65: "OP_VERIF",
    0x66: "OP_VERNOTIF",
    0x67: "OP_ELSE",
    0x68: "OP_ENDIF",
    0x69: "OP_VERIFY",
    0x6A: "OP_RETURN",
    0x6B: "OP_TOALTSTACK",
    0x6C: "OP_FROMALTSTACK",
    0x6D: "OP_2DROP",
    0x6E: "OP_2DUP",
    0x6F: "OP_3DUP",
    0x70: "OP_2OVER",
    0x71: "OP_2ROT",
    0x72: "OP_2SWAP",
    0x73: "OP_IFDUP",
    0x74: "OP_DEPTH",
    0x75: "OP_DROP",
    0x76: "OP_DUP",
    0x77: "OP_NIP",
    0x78: "OP_OVER",
    0x79: "OP_PICK",
    0x7A: "OP_ROLL",
    0x7B: "OP_ROT",
    0x7C: "OP_SWAP",
    0x7D: "OP_TUCK",
    0x7E: "OP_CAT",
    0x7F: "OP_SUBSTR",
    0x80: "OP_LEFT",
    0x81: "OP_RIGHT",
    0x82: "OP_SIZE",
    0x83: "OP_INVERT",
    0x84: "OP_AND",
    0x85: "OP_OR",
    0x86: "OP_XOR",
    0x87: "OP_EQUAL",
    0x88: "OP_EQUALVERIFY",
    0x89: "OP_RESERVED1",
    0x8A: "OP_RESERVED2",
    0x8B: "OP_1ADD",
    0x8C: "OP_1SUB",
    0x8D: "OP_2MUL",
    0x8E: "OP_2DIV",
    0x8F: "OP_NEGATE",
    0x90: "OP_ABS",
    0x91: "OP_NOT",
    0x92: "OP_0NOTEQUAL",
    0x93: "OP_ADD",
    0x94: "OP_SUB",
    0x95: "OP_MUL",
    0x96: "OP_DIV",
    0x97: "OP_MOD",
    0x98: "OP_LSHIFT",
    0x99: "OP_RSHIFT",
    0x9A: "OP_BOOLAND",
    0x9B: "OP_BOOLOR",
    0x9C: "OP_NUMEQUAL",
    0x9D: "OP_NUMEQUALVERIFY",
    0x9E: "OP_NUMNOTEQUAL",
    0x9F: "OP_LESSTHAN",
    0xA0: "OP_GREATERTHAN",
    0xA1: "OP_LESSTHANOREQUAL",
    0xA2: "OP_GREATERTHANOREQUAL",
    0xA3: "OP_MIN",
    0xA4: "OP_MAX",
    0xA5: "OP_WITHIN",
    0xA6: "OP_RIPEMD160",
    0xA7: "OP_SHA1",
    0xA8: "OP_SHA256",
    0xA9: "OP_HASH160",
    0xAA: "OP_HASH256",
    0xAB: "OP_CODESEPARATOR",
    0xAC: "OP_CHECKSIG",
    0xAD: "OP_CHECKSIGVERIFY",
    0xAE: "OP_CHECKMULTISIG",
    0xAF: "OP_CHECKMULTISIGVERIFY",
    0xB0: "OP_NOP1",
    0xB1: "OP_CHECKLOCKTIMEVERIFY",
    0xB2: "OP_CHECKSEQUENCEVERIFY",
    0xB3: "OP_NOP4",
    0xB4: "OP_NOP5",
    0xB5: "OP_NOP6",
    0xB6: "OP_NOP7",
    0xB7: "OP_NOP8",
    0xB8: "OP_NOP9",
    0xB9: "OP_NOP10",
    0xBA: "OP_CHECKSIGADD",
    0xFD: "OP_PUBKEYHASH",
    0xFE: "OP_PUBKEY",
    0xFF: "OP_INVALIDOPCODE",
}

OPCODE_VALUES: dict = {v: k for k, v in OPCODE_NAMES.items()}
# Add common aliases
OPCODE_VALUES["OP_FALSE"] = 0x00
OPCODE_VALUES["OP_TRUE"]  = 0x51
OPCODE_VALUES["OP_CLTV"]  = 0xB1
OPCODE_VALUES["OP_CSV"]   = 0xB2

# Also used by __init__.py re-export
OPCODES = OPCODE_VALUES


# ---------------------------------------------------------------------------
# Script class
# ---------------------------------------------------------------------------

class Script:
    """Represents a Bitcoin script as raw bytes with parsing utilities.

    Parameters
    ----------
    raw:
        Raw script bytes (the script_pubkey or script_sig serialisation,
        NOT prefixed by a CompactSize length).
    """

    def __init__(self, raw: bytes):
        if not isinstance(raw, (bytes, bytearray)):
            raise TypeError(f"Script: raw must be bytes, got {type(raw).__name__}")
        self._raw = bytes(raw)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse(self) -> list:
        """Parse the script into a list of tokens.

        Each token is either:
        - An ``int`` (opcode value), or
        - ``bytes`` (a data push payload).

        Returns
        -------
        List of int and bytes tokens.  Malformed push instructions return
        a ``bytes`` sentinel of the partial data available.
        """
        tokens = []
        i = 0
        raw = self._raw
        n = len(raw)

        while i < n:
            byte = raw[i]
            i += 1

            if byte == 0x00:
                # OP_0 — push empty byte array
                tokens.append(b"")
            elif 0x01 <= byte <= 0x4B:
                # Direct push: next `byte` bytes are data
                end = i + byte
                tokens.append(raw[i:end])
                i = end
            elif byte == OP_PUSHDATA1:
                if i >= n:
                    break
                length = raw[i]
                i += 1
                tokens.append(raw[i: i + length])
                i += length
            elif byte == OP_PUSHDATA2:
                if i + 2 > n:
                    break
                length = int.from_bytes(raw[i: i + 2], "little")
                i += 2
                tokens.append(raw[i: i + length])
                i += length
            elif byte == OP_PUSHDATA4:
                if i + 4 > n:
                    break
                length = int.from_bytes(raw[i: i + 4], "little")
                i += 4
                tokens.append(raw[i: i + length])
                i += length
            else:
                tokens.append(byte)

        return tokens

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self) -> str:
        """Identify the standard script type.

        Returns one of:
        ``'p2pkh'``, ``'p2sh'``, ``'p2wpkh'``, ``'p2wsh'``, ``'p2tr'``,
        ``'multisig'``, ``'op_return'``, ``'p2pk'``, ``'unknown'``.
        """
        raw = self._raw
        n = len(raw)

        # P2PKH: OP_DUP OP_HASH160 <20> OP_EQUALVERIFY OP_CHECKSIG
        if (
            n == 25
            and raw[0] == OP_DUP
            and raw[1] == OP_HASH160
            and raw[2] == 0x14  # push 20 bytes
            and raw[23] == OP_EQUALVERIFY
            and raw[24] == OP_CHECKSIG
        ):
            return "p2pkh"

        # P2SH: OP_HASH160 <20> OP_EQUAL
        if (
            n == 23
            and raw[0] == OP_HASH160
            and raw[1] == 0x14
            and raw[22] == OP_EQUAL
        ):
            return "p2sh"

        # P2WPKH: OP_0 <20>
        if n == 22 and raw[0] == OP_0 and raw[1] == 0x14:
            return "p2wpkh"

        # P2WSH: OP_0 <32>
        if n == 34 and raw[0] == OP_0 and raw[1] == 0x20:
            return "p2wsh"

        # P2TR (Taproot): OP_1 <32>
        if n == 34 and raw[0] == OP_1 and raw[1] == 0x20:
            return "p2tr"

        # OP_RETURN
        if n >= 1 and raw[0] == OP_RETURN:
            return "op_return"

        # P2PK: <pubkey 33 or 65> OP_CHECKSIG
        if n in (35, 67) and raw[-1] == OP_CHECKSIG:
            push_len = raw[0]
            if push_len == n - 2:
                return "p2pk"

        # Multisig: OP_m <pubkeys> OP_n OP_CHECKMULTISIG
        if self._is_multisig():
            return "multisig"

        return "unknown"

    def _is_multisig(self) -> bool:
        """Return True if this looks like a bare multisig script."""
        raw = self._raw
        n = len(raw)
        if n < 3:
            return False
        # Last byte must be OP_CHECKMULTISIG
        if raw[-1] != OP_CHECKMULTISIG:
            return False
        # Last opcode before CHECKMULTISIG must be OP_1..OP_16
        n_byte = raw[-2]
        if not (OP_1 <= n_byte <= OP_16):
            return False
        # First byte must be OP_1..OP_16
        m_byte = raw[0]
        if not (OP_1 <= m_byte <= OP_16):
            return False
        m = m_byte - OP_1 + 1
        n_keys = n_byte - OP_1 + 1
        return 1 <= m <= n_keys <= 16

    def is_standard(self) -> bool:
        """Return True if this is a standard (relay-safe) script type."""
        script_type = self.classify()
        return script_type in ("p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr", "p2pk",
                               "multisig", "op_return")

    def is_witness(self) -> bool:
        """Return True if this is a native SegWit output script (v0 or v1)."""
        return self.classify() in ("p2wpkh", "p2wsh", "p2tr")

    # ------------------------------------------------------------------
    # Address extraction
    # ------------------------------------------------------------------

    def get_addresses(self, network: str = "mainnet") -> list:
        """Extract human-readable addresses from this script.

        Parameters
        ----------
        network:
            'mainnet', 'testnet', or 'regtest'.  Determines address prefixes.

        Returns
        -------
        List of address strings.  May be empty for non-standard scripts.
        """
        from .encoding import base58check_encode, segwit_addr_encode

        script_type = self.classify()
        raw = self._raw

        # Network params
        if network == "testnet":
            hrp = "tb"
            p2pkh_version = 0x6F
            p2sh_version = 0xC4
        elif network == "regtest":
            hrp = "bcrt"
            p2pkh_version = 0x6F
            p2sh_version = 0xC4
        else:  # mainnet
            hrp = "bc"
            p2pkh_version = 0x00
            p2sh_version = 0x05

        try:
            if script_type == "p2pkh":
                pubkey_hash = raw[3:23]
                return [base58check_encode(p2pkh_version, pubkey_hash)]

            elif script_type == "p2sh":
                script_hash = raw[2:22]
                return [base58check_encode(p2sh_version, script_hash)]

            elif script_type == "p2wpkh":
                witprog = raw[2:22]
                return [segwit_addr_encode(hrp, 0, witprog)]

            elif script_type == "p2wsh":
                witprog = raw[2:34]
                return [segwit_addr_encode(hrp, 0, witprog)]

            elif script_type == "p2tr":
                witprog = raw[2:34]
                return [segwit_addr_encode(hrp, 1, witprog)]

        except Exception:
            pass

        return []

    # ------------------------------------------------------------------
    # Multisig helpers
    # ------------------------------------------------------------------

    def get_required_sigs(self) -> int:
        """Return the required-signature count for a multisig script.

        Returns 0 for non-multisig scripts, 1 for P2PK/P2PKH/P2WPKH, or
        the m value for m-of-n multisig.
        """
        script_type = self.classify()
        if script_type in ("p2pkh", "p2pk", "p2wpkh", "p2wsh", "p2sh", "p2tr"):
            return 1
        if script_type == "multisig":
            return self._raw[0] - OP_1 + 1
        return 0

    # ------------------------------------------------------------------
    # Disassembly
    # ------------------------------------------------------------------

    def disassemble(self) -> str:
        """Return a human-readable disassembly of the script.

        Data pushes are shown as hex strings.  Opcodes are shown by name.
        Unknown opcodes are shown as ``OP_UNKNOWN_0xXX``.
        """
        parts = []
        for token in self.parse():
            if isinstance(token, bytes):
                parts.append(token.hex() if token else "OP_0")
            else:
                name = OPCODE_NAMES.get(token, f"OP_UNKNOWN_0x{token:02X}")
                parts.append(name)
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def to_hex(self) -> str:
        """Return the raw script as a lowercase hex string."""
        return self._raw.hex()

    def get_size(self) -> int:
        """Return the byte length of the raw script."""
        return len(self._raw)

    def __bytes__(self) -> bytes:
        return self._raw

    def __len__(self) -> int:
        return len(self._raw)

    def __eq__(self, other) -> bool:
        if isinstance(other, Script):
            return self._raw == other._raw
        if isinstance(other, bytes):
            return self._raw == other
        return NotImplemented

    def __repr__(self) -> str:
        return (
            f"Script(type={self.classify()!r}, "
            f"size={self.get_size()}, hex={self.to_hex()[:40]!r})"
        )


# ---------------------------------------------------------------------------
# ScriptBuilder
# ---------------------------------------------------------------------------

class ScriptBuilder:
    """Fluent builder for constructing Bitcoin scripts byte-by-byte.

    Usage example::

        script = (
            ScriptBuilder()
            .push_op(OP_DUP)
            .push_op(OP_HASH160)
            .push_data(pubkey_hash)
            .push_op(OP_EQUALVERIFY)
            .push_op(OP_CHECKSIG)
            .build()
        )
    """

    def __init__(self):
        self._buf = bytearray()

    def push_data(self, data: bytes) -> "ScriptBuilder":
        """Push raw *data* bytes onto the script with the minimal push opcode."""
        n = len(data)
        if n == 0:
            self._buf.append(OP_0)
        elif n <= 0x4B:
            self._buf.append(n)
            self._buf.extend(data)
        elif n <= 0xFF:
            self._buf.append(OP_PUSHDATA1)
            self._buf.append(n)
            self._buf.extend(data)
        elif n <= 0xFFFF:
            self._buf.append(OP_PUSHDATA2)
            self._buf.extend(n.to_bytes(2, "little"))
            self._buf.extend(data)
        else:
            self._buf.append(OP_PUSHDATA4)
            self._buf.extend(n.to_bytes(4, "little"))
            self._buf.extend(data)
        return self

    def push_int(self, n: int) -> "ScriptBuilder":
        """Push a small integer (−1 to 16) using the appropriate opcode.

        For values outside this range, the integer is serialised as a
        script number (little-endian, sign-magnitude) and pushed as data.
        """
        if n == 0:
            self._buf.append(OP_0)
        elif n == -1:
            self._buf.append(OP_1NEGATE)
        elif 1 <= n <= 16:
            self._buf.append(OP_1 + n - 1)
        else:
            # Serialise as script number (little-endian, sign-magnitude)
            negative = n < 0
            absval = abs(n)
            result = []
            while absval:
                result.append(absval & 0xFF)
                absval >>= 8
            if result[-1] & 0x80:
                result.append(0x80 if negative else 0x00)
            elif negative:
                result[-1] |= 0x80
            self.push_data(bytes(result))
        return self

    def push_op(self, opcode: int) -> "ScriptBuilder":
        """Append a single opcode byte."""
        self._buf.append(opcode & 0xFF)
        return self

    def build(self) -> Script:
        """Return the assembled :class:`Script`."""
        return Script(bytes(self._buf))

    def __bytes__(self) -> bytes:
        return bytes(self._buf)


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------

def build_p2pkh_script(pubkey_hash: bytes) -> Script:
    """Build a P2PKH locking script.

    Structure: OP_DUP OP_HASH160 <pubkey_hash(20)> OP_EQUALVERIFY OP_CHECKSIG

    Parameters
    ----------
    pubkey_hash:
        20-byte hash160 of the compressed public key.
    """
    if len(pubkey_hash) != 20:
        raise ValueError(
            f"build_p2pkh_script: pubkey_hash must be 20 bytes, got {len(pubkey_hash)}"
        )
    return (
        ScriptBuilder()
        .push_op(OP_DUP)
        .push_op(OP_HASH160)
        .push_data(pubkey_hash)
        .push_op(OP_EQUALVERIFY)
        .push_op(OP_CHECKSIG)
        .build()
    )


def build_p2sh_script(script_hash: bytes) -> Script:
    """Build a P2SH locking script.

    Structure: OP_HASH160 <script_hash(20)> OP_EQUAL

    Parameters
    ----------
    script_hash:
        20-byte hash160 of the serialised redeem script.
    """
    if len(script_hash) != 20:
        raise ValueError(
            f"build_p2sh_script: script_hash must be 20 bytes, got {len(script_hash)}"
        )
    return (
        ScriptBuilder()
        .push_op(OP_HASH160)
        .push_data(script_hash)
        .push_op(OP_EQUAL)
        .build()
    )


def build_p2wpkh_script(pubkey_hash: bytes) -> Script:
    """Build a P2WPKH (native SegWit v0) locking script.

    Structure: OP_0 <pubkey_hash(20)>

    Parameters
    ----------
    pubkey_hash:
        20-byte hash160 of the compressed public key.
    """
    if len(pubkey_hash) != 20:
        raise ValueError(
            f"build_p2wpkh_script: pubkey_hash must be 20 bytes, got {len(pubkey_hash)}"
        )
    return (
        ScriptBuilder()
        .push_op(OP_0)
        .push_data(pubkey_hash)
        .build()
    )


def build_p2wsh_script(script_hash: bytes) -> Script:
    """Build a P2WSH (native SegWit v0) locking script.

    Structure: OP_0 <script_hash(32)>

    Parameters
    ----------
    script_hash:
        32-byte SHA-256 of the witness script.
    """
    if len(script_hash) != 32:
        raise ValueError(
            f"build_p2wsh_script: script_hash must be 32 bytes, got {len(script_hash)}"
        )
    return (
        ScriptBuilder()
        .push_op(OP_0)
        .push_data(script_hash)
        .build()
    )


def build_p2tr_script(tweaked_pubkey: bytes) -> Script:
    """Build a P2TR (Taproot, BIP-341) locking script.

    Structure: OP_1 <tweaked_pubkey(32)>

    Parameters
    ----------
    tweaked_pubkey:
        32-byte x-only tweaked internal public key.
    """
    if len(tweaked_pubkey) != 32:
        raise ValueError(
            f"build_p2tr_script: tweaked_pubkey must be 32 bytes, got {len(tweaked_pubkey)}"
        )
    return (
        ScriptBuilder()
        .push_op(OP_1)
        .push_data(tweaked_pubkey)
        .build()
    )


def build_multisig_script(m: int, pubkeys: list) -> Script:
    """Build a bare m-of-n multisig locking script.

    Structure: OP_m <pubkey1> <pubkey2> ... <pubkeyN> OP_n OP_CHECKMULTISIG

    Parameters
    ----------
    m:
        Required number of signatures (1-16).
    pubkeys:
        List of compressed public key bytes (each 33 bytes).

    Raises
    ------
    ValueError if m/n are out of range or pubkeys are malformed.
    """
    n = len(pubkeys)
    if not 1 <= m <= n <= 16:
        raise ValueError(
            f"build_multisig_script: require 1 <= m({m}) <= n({n}) <= 16"
        )
    for i, pk in enumerate(pubkeys):
        if len(pk) not in (33, 65):
            raise ValueError(
                f"build_multisig_script: pubkey[{i}] must be 33 or 65 bytes, "
                f"got {len(pk)}"
            )
    builder = ScriptBuilder().push_int(m)
    for pk in pubkeys:
        builder.push_data(pk)
    builder.push_int(n).push_op(OP_CHECKMULTISIG)
    return builder.build()


def build_op_return_script(data: bytes) -> Script:
    """Build an OP_RETURN (provably unspendable) output script.

    Structure: OP_RETURN [data]

    Parameters
    ----------
    data:
        Up to 80 bytes of arbitrary data (Bitcoin standard policy limit).

    Raises
    ------
    ValueError if data exceeds 80 bytes.
    """
    if len(data) > 80:
        raise ValueError(
            f"build_op_return_script: data must be <= 80 bytes, got {len(data)}"
        )
    builder = ScriptBuilder().push_op(OP_RETURN)
    if data:
        builder.push_data(data)
    return builder.build()


def build_timelock_script(locktime: int, pubkey_hash: bytes) -> Script:
    """Build a CLTV-timelocked P2PKH script.

    Structure:
        <locktime> OP_CHECKLOCKTIMEVERIFY OP_DROP
        OP_DUP OP_HASH160 <pubkey_hash> OP_EQUALVERIFY OP_CHECKSIG

    This is the standard pattern for timelocked outputs — the UTXO cannot
    be spent until the block height or Unix timestamp exceeds *locktime*.

    Parameters
    ----------
    locktime:
        Block height (<500_000_000) or Unix timestamp (>=500_000_000).
    pubkey_hash:
        20-byte hash160 of the recipient's compressed public key.
    """
    if len(pubkey_hash) != 20:
        raise ValueError(
            f"build_timelock_script: pubkey_hash must be 20 bytes, got {len(pubkey_hash)}"
        )
    if locktime < 0:
        raise ValueError(f"build_timelock_script: locktime must be non-negative")
    return (
        ScriptBuilder()
        .push_int(locktime)
        .push_op(OP_CHECKLOCKTIMEVERIFY)
        .push_op(OP_DROP)
        .push_op(OP_DUP)
        .push_op(OP_HASH160)
        .push_data(pubkey_hash)
        .push_op(OP_EQUALVERIFY)
        .push_op(OP_CHECKSIG)
        .build()
    )


# ---------------------------------------------------------------------------
# Module-level functional API (used by __init__.py)
# ---------------------------------------------------------------------------

def parse_script(raw: bytes) -> list:
    """Parse raw script bytes into a list of tokens.  See :meth:`Script.parse`."""
    return Script(raw).parse()


def classify_script(raw: bytes) -> str:
    """Classify raw script bytes.  See :meth:`Script.classify`."""
    return Script(raw).classify()


def extract_addresses(raw: bytes, network: str = "mainnet") -> list:
    """Extract addresses from raw script bytes."""
    return Script(raw).get_addresses(network=network)


def is_standard(raw: bytes) -> bool:
    """Return True if the raw script is standard."""
    return Script(raw).is_standard()


def estimate_script_size(script_type: str, n_keys: int = 1) -> int:
    """Return the approximate byte size of a script type's serialised form.

    Useful for fee estimation without constructing a full transaction.

    Parameters
    ----------
    script_type:
        One of: 'p2pkh', 'p2sh', 'p2wpkh', 'p2wsh', 'p2tr', 'p2pk',
        'multisig', 'op_return'.
    n_keys:
        Number of keys (only relevant for 'multisig').

    Returns
    -------
    Estimated byte count.
    """
    sizes = {
        "p2pkh":    25,
        "p2sh":     23,
        "p2wpkh":   22,
        "p2wsh":    34,
        "p2tr":     34,
        "p2pk":     35,
        "op_return": 13,  # OP_RETURN + 1-byte push + ~10 bytes data (estimate)
    }
    if script_type == "multisig":
        # OP_m + n*(1 + 33) + OP_n + OP_CHECKMULTISIG
        return 3 + n_keys * 34
    return sizes.get(script_type, 25)


def disassemble(raw: bytes) -> str:
    """Disassemble raw script bytes into a human-readable string."""
    return Script(raw).disassemble()
