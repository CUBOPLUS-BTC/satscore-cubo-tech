"""
app.btcprotocol.protocol
===================
Bitcoin protocol data structures — educational reference implementation.

Provides serialisation/deserialisation for:
- Block headers (80 bytes)
- Transactions (legacy and SegWit)
- Transaction inputs and outputs
- Complete blocks

Also defines network configuration constants for mainnet, testnet,
signet, and regtest.

No private-key operations are performed here.  All serialisation follows
the Bitcoin P2P wire format as specified in the Bitcoin Core source and the
developer documentation at https://developer.bitcoin.org/.

Public API
----------
BlockHeader   - parse/serialise 80-byte block headers, validate PoW
Transaction   - parse/serialise legacy and SegWit transactions
TxInput       - transaction input with prev_txid, prev_index, script_sig, sequence
TxOutput      - transaction output with value and script_pubkey
Block         - full block (header + transactions)
MAINNET       - network configuration dict
TESTNET       - network configuration dict
SIGNET        - network configuration dict
REGTEST       - network configuration dict
"""

from __future__ import annotations
import struct
import time
from typing import List, Optional

from .hashing import double_sha256, merkle_root, compute_target, difficulty_from_target
from .encoding import (
    compact_size_encode,
    compact_size_decode,
    int_to_little_endian,
    little_endian_to_int,
    bytes_to_hex,
    reverse_bytes,
)
from .script import Script


# ---------------------------------------------------------------------------
# Network configuration constants
# ---------------------------------------------------------------------------

MAINNET = {
    "name": "mainnet",
    "magic": bytes([0xF9, 0xBE, 0xB4, 0xD9]),
    "default_port": 8333,
    "p2pkh_version": 0x00,
    "p2sh_version": 0x05,
    "wif_version": 0x80,
    "xpub_version": bytes([0x04, 0x88, 0xB2, 0x1E]),
    "xprv_version": bytes([0x04, 0x88, 0xAD, 0xE4]),
    "bech32_hrp": "bc",
    "genesis_hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "genesis_time": 1231006505,
    "genesis_bits": 0x1D00FFFF,
    "genesis_nonce": 2083236893,
}

TESTNET = {
    "name": "testnet",
    "magic": bytes([0x0B, 0x11, 0x09, 0x07]),
    "default_port": 18333,
    "p2pkh_version": 0x6F,
    "p2sh_version": 0xC4,
    "wif_version": 0xEF,
    "xpub_version": bytes([0x04, 0x35, 0x87, 0xCF]),
    "xprv_version": bytes([0x04, 0x35, 0x83, 0x94]),
    "bech32_hrp": "tb",
    "genesis_hash": "000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943",
    "genesis_time": 1296688602,
    "genesis_bits": 0x1D00FFFF,
    "genesis_nonce": 414098458,
}

SIGNET = {
    "name": "signet",
    "magic": bytes([0x0A, 0x03, 0xCF, 0x40]),
    "default_port": 38333,
    "p2pkh_version": 0x6F,
    "p2sh_version": 0xC4,
    "wif_version": 0xEF,
    "xpub_version": bytes([0x04, 0x35, 0x87, 0xCF]),
    "xprv_version": bytes([0x04, 0x35, 0x83, 0x94]),
    "bech32_hrp": "tb",
    "genesis_hash": "00000008819873e925422c1ff0f99f7cc9bbb232af63a077a480a3633bee1ef6",
    "genesis_time": 1598918400,
    "genesis_bits": 0x1E0377AE,
    "genesis_nonce": 52613770,
}

REGTEST = {
    "name": "regtest",
    "magic": bytes([0xFA, 0xBF, 0xB5, 0xDA]),
    "default_port": 18444,
    "p2pkh_version": 0x6F,
    "p2sh_version": 0xC4,
    "wif_version": 0xEF,
    "xpub_version": bytes([0x04, 0x35, 0x87, 0xCF]),
    "xprv_version": bytes([0x04, 0x35, 0x83, 0x94]),
    "bech32_hrp": "bcrt",
    "genesis_hash": "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206",
    "genesis_time": 1296688602,
    "genesis_bits": 0x207FFFFF,
    "genesis_nonce": 2,
}

# Sentinel value for OP_RETURN marker in coinbase outputs
_COINBASE_TXID = b"\x00" * 32
_COINBASE_INDEX = 0xFFFFFFFF
_SEGWIT_MARKER = 0x00
_SEGWIT_FLAG   = 0x01


# ---------------------------------------------------------------------------
# BlockHeader
# ---------------------------------------------------------------------------

class BlockHeader:
    """80-byte Bitcoin block header.

    Fields follow the wire format:
    version (4 LE) + prev_hash (32) + merkle_root (32) +
    timestamp (4 LE) + bits (4 LE) + nonce (4 LE) = 80 bytes.

    All hashes are stored in *internal* (little-endian) byte order.
    """

    def __init__(
        self,
        version: int,
        prev_hash: bytes,
        merkle_root_bytes: bytes,
        timestamp: int,
        bits: int,
        nonce: int,
    ):
        if len(prev_hash) != 32:
            raise ValueError(f"BlockHeader: prev_hash must be 32 bytes")
        if len(merkle_root_bytes) != 32:
            raise ValueError(f"BlockHeader: merkle_root must be 32 bytes")
        self.version = version
        self.prev_hash = prev_hash
        self.merkle_root_bytes = merkle_root_bytes
        self.timestamp = timestamp
        self.bits = bits
        self.nonce = nonce

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def serialize(self) -> bytes:
        """Serialise the header to exactly 80 bytes (wire format)."""
        return (
            struct.pack("<I", self.version)
            + self.prev_hash
            + self.merkle_root_bytes
            + struct.pack("<I", self.timestamp)
            + struct.pack("<I", self.bits)
            + struct.pack("<I", self.nonce)
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "BlockHeader":
        """Parse an 80-byte block header from bytes.

        Parameters
        ----------
        data:
            Exactly 80 bytes starting at the block header.

        Raises
        ------
        ValueError if data is shorter than 80 bytes.
        """
        if len(data) < 80:
            raise ValueError(
                f"BlockHeader.deserialize: need 80 bytes, got {len(data)}"
            )
        version = struct.unpack_from("<I", data, 0)[0]
        prev_hash = data[4:36]
        mr = data[36:68]
        timestamp = struct.unpack_from("<I", data, 68)[0]
        bits = struct.unpack_from("<I", data, 72)[0]
        nonce = struct.unpack_from("<I", data, 76)[0]
        return cls(version, prev_hash, mr, timestamp, bits, nonce)

    # ------------------------------------------------------------------
    # Hash / PoW
    # ------------------------------------------------------------------

    def compute_hash(self) -> str:
        """Return the block hash as a big-endian hex string (explorer format).

        This is double-SHA256 of the 80-byte serialised header, reversed.
        """
        raw = self.serialize()
        digest = double_sha256(raw)
        return digest[::-1].hex()

    def get_target(self) -> int:
        """Return the full 256-bit proof-of-work target from the *bits* field."""
        return compute_target(self.bits)

    def get_difficulty(self) -> float:
        """Return the mining difficulty relative to the genesis block target."""
        return difficulty_from_target(self.get_target())

    def validate_pow(self) -> bool:
        """Return True if the block hash meets the declared difficulty target.

        Checks: int(hash_bytes_reversed) < target
        """
        raw = self.serialize()
        digest = double_sha256(raw)
        # Digest is in little-endian; interpret as 256-bit integer
        hash_int = int.from_bytes(digest, "little")
        target = self.get_target()
        return hash_int < target

    def to_dict(self) -> dict:
        """Return the header fields as a JSON-serialisable dict."""
        return {
            "hash": self.compute_hash(),
            "version": self.version,
            "prev_hash": self.prev_hash[::-1].hex(),
            "merkle_root": self.merkle_root_bytes[::-1].hex(),
            "timestamp": self.timestamp,
            "bits": f"0x{self.bits:08X}",
            "nonce": self.nonce,
            "difficulty": self.get_difficulty(),
            "target": hex(self.get_target()),
        }


# ---------------------------------------------------------------------------
# TxInput
# ---------------------------------------------------------------------------

class TxInput:
    """A single transaction input.

    Wire format:
    prev_txid (32, LE) + prev_index (4, LE) +
    script_sig_len (varint) + script_sig + sequence (4, LE)
    """

    def __init__(
        self,
        prev_txid: bytes,
        prev_index: int,
        script_sig: bytes,
        sequence: int = 0xFFFFFFFF,
    ):
        if len(prev_txid) != 32:
            raise ValueError(f"TxInput: prev_txid must be 32 bytes")
        self.prev_txid = prev_txid
        self.prev_index = prev_index
        self.script_sig = script_sig
        self.sequence = sequence

    def serialize(self) -> bytes:
        """Serialise to wire format bytes."""
        return (
            self.prev_txid
            + struct.pack("<I", self.prev_index)
            + compact_size_encode(len(self.script_sig))
            + self.script_sig
            + struct.pack("<I", self.sequence)
        )

    @classmethod
    def deserialize(cls, data: bytes, offset: int = 0) -> tuple:
        """Parse a TxInput from *data* starting at *offset*.

        Returns
        -------
        (TxInput, new_offset: int)
        """
        prev_txid = data[offset: offset + 32]
        if len(prev_txid) != 32:
            raise ValueError("TxInput.deserialize: truncated prev_txid")
        offset += 32

        prev_index = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        script_len, offset = compact_size_decode(data, offset)
        script_sig = data[offset: offset + script_len]
        offset += script_len

        sequence = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        return cls(prev_txid, prev_index, script_sig, sequence), offset

    def is_coinbase(self) -> bool:
        """Return True if this is a coinbase input."""
        return (
            self.prev_txid == _COINBASE_TXID
            and self.prev_index == _COINBASE_INDEX
        )

    def to_dict(self) -> dict:
        """Return JSON-serialisable representation."""
        return {
            "prev_txid": self.prev_txid[::-1].hex(),
            "prev_index": self.prev_index,
            "script_sig": self.script_sig.hex(),
            "sequence": f"0x{self.sequence:08X}",
            "is_coinbase": self.is_coinbase(),
        }


# ---------------------------------------------------------------------------
# TxOutput
# ---------------------------------------------------------------------------

class TxOutput:
    """A single transaction output.

    Wire format: value (8, LE) + script_pubkey_len (varint) + script_pubkey
    """

    def __init__(self, value: int, script_pubkey: bytes):
        if value < 0:
            raise ValueError(f"TxOutput: value must be non-negative, got {value}")
        self.value = value          # satoshis
        self.script_pubkey = script_pubkey

    def serialize(self) -> bytes:
        """Serialise to wire format bytes."""
        return (
            struct.pack("<q", self.value)
            + compact_size_encode(len(self.script_pubkey))
            + self.script_pubkey
        )

    @classmethod
    def deserialize(cls, data: bytes, offset: int = 0) -> tuple:
        """Parse a TxOutput from *data* starting at *offset*.

        Returns
        -------
        (TxOutput, new_offset: int)
        """
        value = struct.unpack_from("<q", data, offset)[0]
        offset += 8

        script_len, offset = compact_size_decode(data, offset)
        script_pubkey = data[offset: offset + script_len]
        offset += script_len

        return cls(value, script_pubkey), offset

    def get_address(self, network: str = "mainnet") -> str:
        """Extract the address from this output's script.

        Returns the address string, or empty string for non-standard scripts.
        """
        addresses = Script(self.script_pubkey).get_addresses(network=network)
        return addresses[0] if addresses else ""

    def to_dict(self) -> dict:
        """Return JSON-serialisable representation."""
        return {
            "value_sat": self.value,
            "value_btc": self.value / 1e8,
            "script_pubkey": self.script_pubkey.hex(),
            "script_type": Script(self.script_pubkey).classify(),
            "address": self.get_address(),
        }


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction:
    """A Bitcoin transaction — legacy or SegWit (BIP-141).

    Wire format (legacy):
    version (4 LE) + vin_count (varint) + inputs + vout_count (varint) +
    outputs + locktime (4 LE)

    Wire format (SegWit):
    version (4 LE) + marker(0x00) + flag(0x01) + vin_count + inputs +
    vout_count + outputs + witness_data + locktime (4 LE)

    The txid is always computed from the legacy (non-witness) serialisation.
    The wtxid uses the full witness serialisation.
    """

    def __init__(
        self,
        version: int,
        inputs: List[TxInput],
        outputs: List[TxOutput],
        locktime: int = 0,
        witnesses: Optional[List[List[bytes]]] = None,
    ):
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.locktime = locktime
        # witnesses[i] is the list of stack items for input i
        self.witnesses: List[List[bytes]] = witnesses or []

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def serialize(self) -> bytes:
        """Serialise to legacy (non-witness) format — used for txid computation."""
        buf = struct.pack("<i", self.version)
        buf += compact_size_encode(len(self.inputs))
        for txin in self.inputs:
            buf += txin.serialize()
        buf += compact_size_encode(len(self.outputs))
        for txout in self.outputs:
            buf += txout.serialize()
        buf += struct.pack("<I", self.locktime)
        return buf

    def serialize_witness(self) -> bytes:
        """Serialise including witness data — used for wtxid and network transmission."""
        buf = struct.pack("<i", self.version)
        buf += bytes([_SEGWIT_MARKER, _SEGWIT_FLAG])
        buf += compact_size_encode(len(self.inputs))
        for txin in self.inputs:
            buf += txin.serialize()
        buf += compact_size_encode(len(self.outputs))
        for txout in self.outputs:
            buf += txout.serialize()
        # Witness for each input
        for i in range(len(self.inputs)):
            witness = self.witnesses[i] if i < len(self.witnesses) else []
            buf += compact_size_encode(len(witness))
            for item in witness:
                buf += compact_size_encode(len(item))
                buf += item
        buf += struct.pack("<I", self.locktime)
        return buf

    @classmethod
    def deserialize(cls, data: bytes, offset: int = 0) -> tuple:
        """Parse a transaction from *data*.

        Handles both legacy and SegWit transactions automatically.

        Returns
        -------
        (Transaction, new_offset: int)
        """
        start = offset
        version = struct.unpack_from("<i", data, offset)[0]
        offset += 4

        # Detect SegWit marker
        is_segwit = False
        if offset + 2 <= len(data) and data[offset] == _SEGWIT_MARKER and data[offset + 1] == _SEGWIT_FLAG:
            is_segwit = True
            offset += 2

        # Inputs
        vin_count, offset = compact_size_decode(data, offset)
        inputs = []
        for _ in range(vin_count):
            txin, offset = TxInput.deserialize(data, offset)
            inputs.append(txin)

        # Outputs
        vout_count, offset = compact_size_decode(data, offset)
        outputs = []
        for _ in range(vout_count):
            txout, offset = TxOutput.deserialize(data, offset)
            outputs.append(txout)

        # Witness data
        witnesses: List[List[bytes]] = []
        if is_segwit:
            for _ in range(vin_count):
                stack_item_count, offset = compact_size_decode(data, offset)
                stack: List[bytes] = []
                for _ in range(stack_item_count):
                    item_len, offset = compact_size_decode(data, offset)
                    stack.append(data[offset: offset + item_len])
                    offset += item_len
                witnesses.append(stack)

        locktime = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        return cls(version, inputs, outputs, locktime, witnesses if is_segwit else None), offset

    # ------------------------------------------------------------------
    # IDs
    # ------------------------------------------------------------------

    def compute_txid(self) -> str:
        """Compute the txid (legacy serialisation hash, reversed hex)."""
        raw = self.serialize()
        return double_sha256(raw)[::-1].hex()

    def compute_wtxid(self) -> str:
        """Compute the wtxid (witness serialisation hash, reversed hex).

        For non-SegWit transactions, wtxid == txid.
        """
        if self.is_segwit():
            raw = self.serialize_witness()
        else:
            raw = self.serialize()
        return double_sha256(raw)[::-1].hex()

    # ------------------------------------------------------------------
    # Size / weight (BIP-141)
    # ------------------------------------------------------------------

    def get_size(self) -> int:
        """Raw serialised size in bytes (legacy, no witness)."""
        return len(self.serialize())

    def get_vsize(self) -> int:
        """Virtual size in virtual bytes (ceil(weight / 4))."""
        return (self.get_weight() + 3) // 4

    def get_weight(self) -> int:
        """Transaction weight units (BIP-141).

        weight = (non-witness size) * 4 + witness_size * 1
        For legacy transactions, weight = size * 4.
        """
        if not self.is_segwit():
            return self.get_size() * 4

        # Break down legacy vs witness bytes
        # Legacy bytes: version(4) + marker/flag(0, not counted) +
        #   vin count + inputs + vout count + outputs + locktime(4)
        legacy_size = len(self.serialize())
        witness_size = len(self.serialize_witness()) - legacy_size - 2  # subtract marker+flag
        return legacy_size * 4 + witness_size + 2  # marker+flag weigh 1 each

    # ------------------------------------------------------------------
    # Property checks
    # ------------------------------------------------------------------

    def is_segwit(self) -> bool:
        """Return True if this transaction has witness data."""
        return bool(self.witnesses) and any(self.witnesses)

    def is_coinbase(self) -> bool:
        """Return True if this is a coinbase transaction."""
        return (
            len(self.inputs) == 1
            and self.inputs[0].is_coinbase()
        )

    def get_fee(self, input_values: List[int]) -> int:
        """Compute the transaction fee in satoshis.

        Parameters
        ----------
        input_values:
            List of input values in satoshis (in the same order as self.inputs).

        Returns
        -------
        Fee in satoshis (non-negative).  Returns 0 if inputs don't cover outputs
        (which would indicate a malformed/incomplete transaction).
        """
        if len(input_values) != len(self.inputs):
            raise ValueError(
                f"get_fee: expected {len(self.inputs)} input values, "
                f"got {len(input_values)}"
            )
        total_in = sum(input_values)
        total_out = sum(o.value for o in self.outputs)
        return max(0, total_in - total_out)

    def to_dict(self) -> dict:
        """Return JSON-serialisable representation."""
        return {
            "txid": self.compute_txid(),
            "wtxid": self.compute_wtxid(),
            "version": self.version,
            "size": self.get_size(),
            "vsize": self.get_vsize(),
            "weight": self.get_weight(),
            "locktime": self.locktime,
            "is_coinbase": self.is_coinbase(),
            "is_segwit": self.is_segwit(),
            "vin": [inp.to_dict() for inp in self.inputs],
            "vout": [out.to_dict() for out in self.outputs],
            "witness": [
                [item.hex() for item in stack] for stack in self.witnesses
            ],
        }


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

class Block:
    """A complete Bitcoin block: header + list of transactions.

    The block is valid when:
    1. The block header's merkle_root matches the computed Merkle root of txids.
    2. The header's hash meets the proof-of-work target encoded in bits.
    3. The first transaction is a coinbase.
    """

    def __init__(self, header: BlockHeader, transactions: List[Transaction]):
        self.header = header
        self.transactions = transactions

    # ------------------------------------------------------------------
    # Merkle validation
    # ------------------------------------------------------------------

    def get_merkle_root(self) -> str:
        """Compute the Merkle root of all transaction txids.

        Returns the big-endian (display) hex string.
        """
        if not self.transactions:
            return "0" * 64
        txids_internal = [
            bytes.fromhex(tx.compute_txid())[::-1]  # internal byte order
            for tx in self.transactions
        ]
        root = merkle_root(txids_internal)
        return root[::-1].hex()

    def validate_merkle(self) -> bool:
        """Return True if the header's merkle_root matches the computed root."""
        computed = self.get_merkle_root()
        stored = self.header.merkle_root_bytes[::-1].hex()
        return computed == stored

    # ------------------------------------------------------------------
    # Size
    # ------------------------------------------------------------------

    def get_size(self) -> int:
        """Raw block size in bytes (header + txs, no witness serialisation)."""
        return 80 + sum(tx.get_size() for tx in self.transactions)

    def get_weight(self) -> int:
        """Block weight in weight units (BIP-141).

        = header_weight + coinbase_weight + tx_weights
        """
        # Header weighs 4 * 80 = 320 (legacy bytes * 4)
        header_weight = 320
        tx_weight = sum(tx.get_weight() for tx in self.transactions)
        return header_weight + tx_weight

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_tx_count(self) -> int:
        """Number of transactions in this block."""
        return len(self.transactions)

    def get_total_fees(self) -> int:
        """Total fees collected in this block.

        Approximated as: coinbase_output_sum - block_subsidy.
        Returns 0 if there are no transactions or no coinbase.
        """
        if not self.transactions:
            return 0
        # A precise fee calculation requires knowing input values from UTXOs,
        # which requires the full UTXO set.  Return coinbase output as a proxy.
        coinbase = self.transactions[0]
        if not coinbase.is_coinbase():
            return 0
        return sum(o.value for o in coinbase.outputs)

    def to_dict(self) -> dict:
        """Return JSON-serialisable representation."""
        return {
            "hash": self.header.compute_hash(),
            "height": None,  # requires external context
            "header": self.header.to_dict(),
            "tx_count": self.get_tx_count(),
            "size": self.get_size(),
            "weight": self.get_weight(),
            "merkle_root_computed": self.get_merkle_root(),
            "merkle_valid": self.validate_merkle(),
            "pow_valid": self.header.validate_pow(),
            "transactions": [tx.to_dict() for tx in self.transactions],
        }
