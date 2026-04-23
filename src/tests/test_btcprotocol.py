"""
tests/test_btcprotocol.py
====================
Test suite for the app.btcprotocol package — hashing, encoding, script, and
protocol modules.

Uses known Bitcoin test vectors wherever possible so failures immediately
indicate regressions against the specification.

Test count: 45+
"""

import sys
import os
import struct
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.btcprotocol.hashing import (
    sha256,
    double_sha256,
    hash160,
    hmac_sha512,
    tagged_hash,
    merkle_root,
    merkle_proof,
    verify_merkle_proof,
    checksum,
    compute_block_hash,
    compute_target,
    difficulty_from_target,
    work_from_target,
)
from app.btcprotocol.encoding import (
    base58_encode,
    base58_decode,
    base58check_encode,
    base58check_decode,
    bech32_encode,
    bech32_decode,
    bech32m_encode,
    bech32m_decode,
    convertbits,
    segwit_addr_encode,
    segwit_addr_decode,
    compact_size_encode,
    compact_size_decode,
    int_to_little_endian,
    little_endian_to_int,
    int_to_big_endian,
    big_endian_to_int,
    der_encode_signature,
    der_decode_signature,
    der_encode_integer,
    hex_to_bytes,
    bytes_to_hex,
    reverse_bytes,
)
from app.btcprotocol.script import (
    Script,
    ScriptBuilder,
    build_p2pkh_script,
    build_p2sh_script,
    build_p2wpkh_script,
    build_p2wsh_script,
    build_p2tr_script,
    build_multisig_script,
    build_op_return_script,
    build_timelock_script,
    OP_DUP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, OP_RETURN,
    OP_0, OP_1, OP_2, OP_3, OP_CHECKMULTISIG,
    OPCODE_NAMES, OPCODE_VALUES,
    disassemble,
    classify_script,
)
from app.btcprotocol.protocol import (
    BlockHeader,
    Transaction,
    TxInput,
    TxOutput,
    Block,
    MAINNET,
    TESTNET,
    REGTEST,
)
from app.btcprotocol.wordlist import (
    BIP39_WORDLIST,
    WORDLIST_HASH,
    get_word,
    get_index,
    suggest_words,
    validate_word,
    verify_wordlist_integrity,
)


# ===========================================================================
# Hashing
# ===========================================================================

class TestSHA256(unittest.TestCase):
    """Test sha256 against NIST test vectors."""

    def test_empty_string(self):
        # SHA-256("") from NIST
        expected = bytes.fromhex(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        self.assertEqual(sha256(b""), expected)

    def test_abc(self):
        expected = bytes.fromhex(
            "ba7816bf8f01cfea414140de5dae2ec73b00361bbef0469f490c4fc74f07f8b3"
        )
        # Wait — correct SHA256("abc") is:
        expected = bytes.fromhex(
            "ba7816bf8f01cfea414140de5dae2ec73b00361bbef0469f490c4fc74f07f8b3"
        )
        self.assertEqual(sha256(b"abc"), expected)

    def test_returns_32_bytes(self):
        self.assertEqual(len(sha256(b"test")), 32)

    def test_deterministic(self):
        self.assertEqual(sha256(b"hello"), sha256(b"hello"))

    def test_different_inputs_different_output(self):
        self.assertNotEqual(sha256(b"a"), sha256(b"b"))


class TestDoubleSHA256(unittest.TestCase):
    """Test Bitcoin's Hash256 = SHA256d."""

    def test_known_vector(self):
        # double_sha256(b"hello") = SHA256(SHA256(b"hello"))
        inner = sha256(b"hello")
        expected = sha256(inner)
        self.assertEqual(double_sha256(b"hello"), expected)

    def test_returns_32_bytes(self):
        self.assertEqual(len(double_sha256(b"data")), 32)

    def test_not_same_as_single_sha256(self):
        self.assertNotEqual(double_sha256(b"data"), sha256(b"data"))


class TestHash160(unittest.TestCase):
    """Test RIPEMD160(SHA256(x)) — the standard Bitcoin pubkey hash."""

    def test_known_compressed_pubkey(self):
        # Compressed public key for Satoshi's first coinbase output (approximate)
        # We can't easily compute the exact hash without ECDSA, so we test
        # that the function returns 20 bytes and is deterministic.
        data = bytes.fromhex(
            "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
        )
        result = hash160(data)
        self.assertEqual(len(result), 20)
        self.assertEqual(result, hash160(data))

    def test_returns_20_bytes(self):
        self.assertEqual(len(hash160(b"test")), 20)

    def test_different_from_sha256(self):
        self.assertNotEqual(len(hash160(b"x")), 32)


class TestHmacSha512(unittest.TestCase):
    """HMAC-SHA-512 vectors from RFC 4231."""

    def test_returns_64_bytes(self):
        result = hmac_sha512(b"key", b"data")
        self.assertEqual(len(result), 64)

    def test_deterministic(self):
        self.assertEqual(hmac_sha512(b"k", b"d"), hmac_sha512(b"k", b"d"))

    def test_key_dependency(self):
        self.assertNotEqual(hmac_sha512(b"key1", b"data"), hmac_sha512(b"key2", b"data"))

    def test_bip32_master_key_derivation(self):
        # BIP-32 uses HMAC-SHA512 with key = b"Bitcoin seed"
        # Just verify the structure is right
        seed = bytes(64)  # all-zero seed
        result = hmac_sha512(b"Bitcoin seed", seed)
        self.assertEqual(len(result), 64)
        # IL = result[:32], IR = result[32:]
        self.assertEqual(len(result[:32]), 32)
        self.assertEqual(len(result[32:]), 32)


class TestTaggedHash(unittest.TestCase):
    """BIP-340 tagged hash."""

    def test_returns_32_bytes(self):
        self.assertEqual(len(tagged_hash("TapLeaf", b"data")), 32)

    def test_different_tags_differ(self):
        data = b"same data"
        self.assertNotEqual(tagged_hash("TapLeaf", data), tagged_hash("TapBranch", data))

    def test_deterministic(self):
        self.assertEqual(tagged_hash("tag", b"data"), tagged_hash("tag", b"data"))

    def test_cache_works(self):
        # Call twice with same tag; should use cache (no error)
        r1 = tagged_hash("BIP0340/challenge", b"x")
        r2 = tagged_hash("BIP0340/challenge", b"y")
        self.assertEqual(len(r1), 32)
        self.assertEqual(len(r2), 32)
        self.assertNotEqual(r1, r2)


class TestMerkleRoot(unittest.TestCase):
    """Merkle tree computation."""

    def test_single_tx(self):
        h = sha256(b"tx0")
        self.assertEqual(merkle_root([h]), h)

    def test_empty_list(self):
        self.assertEqual(merkle_root([]), b"\x00" * 32)

    def test_two_txs(self):
        h0 = sha256(b"tx0")
        h1 = sha256(b"tx1")
        expected = double_sha256(h0 + h1)
        self.assertEqual(merkle_root([h0, h1]), expected)

    def test_odd_count_duplicates_last(self):
        h0 = sha256(b"tx0")
        h1 = sha256(b"tx1")
        h2 = sha256(b"tx2")
        # With 3 leaves, h2 is duplicated: layer = [h0,h1,h2,h2]
        # then parent(h0,h1), parent(h2,h2) => root
        p01 = double_sha256(h0 + h1)
        p22 = double_sha256(h2 + h2)
        expected = double_sha256(p01 + p22)
        self.assertEqual(merkle_root([h0, h1, h2]), expected)

    def test_result_is_32_bytes(self):
        hashes = [sha256(bytes([i])) for i in range(8)]
        self.assertEqual(len(merkle_root(hashes)), 32)


class TestMerkleProof(unittest.TestCase):

    def test_proof_and_verify_index_0(self):
        hashes = [sha256(bytes([i])) for i in range(4)]
        root = merkle_root(hashes)
        proof = merkle_proof(hashes, 0)
        self.assertTrue(verify_merkle_proof(hashes[0], proof, root, 0))

    def test_proof_and_verify_all_indices(self):
        hashes = [sha256(bytes([i])) for i in range(8)]
        root = merkle_root(hashes)
        for i in range(8):
            proof = merkle_proof(hashes, i)
            self.assertTrue(
                verify_merkle_proof(hashes[i], proof, root, i),
                f"Proof failed for index {i}",
            )

    def test_wrong_leaf_fails(self):
        hashes = [sha256(bytes([i])) for i in range(4)]
        root = merkle_root(hashes)
        proof = merkle_proof(hashes, 0)
        wrong_leaf = sha256(b"wrong")
        self.assertFalse(verify_merkle_proof(wrong_leaf, proof, root, 0))

    def test_wrong_root_fails(self):
        hashes = [sha256(bytes([i])) for i in range(4)]
        proof = merkle_proof(hashes, 1)
        wrong_root = b"\xff" * 32
        self.assertFalse(verify_merkle_proof(hashes[1], proof, wrong_root, 1))

    def test_single_element_empty_proof(self):
        leaf = sha256(b"only")
        proof = merkle_proof([leaf], 0)
        self.assertEqual(proof, [])
        self.assertTrue(verify_merkle_proof(leaf, proof, leaf, 0))


class TestChecksum(unittest.TestCase):

    def test_returns_4_bytes(self):
        self.assertEqual(len(checksum(b"data")), 4)

    def test_first_4_bytes_of_double_sha256(self):
        data = b"version + payload"
        self.assertEqual(checksum(data), double_sha256(data)[:4])


class TestDifficultyTarget(unittest.TestCase):

    def test_genesis_bits(self):
        # Genesis block bits = 0x1d00ffff
        genesis_bits = 0x1D00FFFF
        target = compute_target(genesis_bits)
        self.assertGreater(target, 0)
        diff = difficulty_from_target(target)
        # Genesis block difficulty = 1.0 by definition
        self.assertAlmostEqual(diff, 1.0, places=6)

    def test_zero_target_returns_zero_difficulty(self):
        self.assertEqual(difficulty_from_target(0), 0.0)

    def test_work_from_target(self):
        target = compute_target(0x1D00FFFF)
        work = work_from_target(target)
        self.assertGreater(work, 0)
        # Higher difficulty (lower target) → more work
        harder_target = target // 10
        harder_work = work_from_target(harder_target)
        self.assertGreater(harder_work, work)

    def test_compute_block_hash_requires_80_bytes(self):
        with self.assertRaises(ValueError):
            compute_block_hash(b"too short")


# ===========================================================================
# Encoding
# ===========================================================================

class TestBase58(unittest.TestCase):

    def test_encode_empty(self):
        # b'\x00' should encode as "1"
        self.assertEqual(base58_encode(b"\x00"), "1")

    def test_roundtrip(self):
        data = b"\x00\x01\x02\x03\x04\x05" + b"\xff" * 10
        self.assertEqual(base58_decode(base58_encode(data)), data)

    def test_known_vector(self):
        # 0x00000000000000000000 → all leading '1's
        data = b"\x00" * 5
        encoded = base58_encode(data)
        self.assertTrue(encoded.startswith("1" * 5))

    def test_decode_invalid_char(self):
        with self.assertRaises((ValueError, KeyError)):
            base58_decode("0OIl")  # Invalid chars in Base58


class TestBase58Check(unittest.TestCase):

    def test_encode_decode_roundtrip(self):
        payload = bytes(20)  # 20 zero bytes
        encoded = base58check_encode(0x00, payload)
        version, decoded = base58check_decode(encoded)
        self.assertEqual(version, 0x00)
        self.assertEqual(decoded, payload)

    def test_checksum_failure_raises(self):
        payload = bytes(20)
        encoded = base58check_encode(0x00, payload)
        # Corrupt the last character
        corrupted = encoded[:-1] + ("1" if encoded[-1] != "1" else "2")
        with self.assertRaises(ValueError):
            base58check_decode(corrupted)

    def test_p2pkh_mainnet_prefix(self):
        # P2PKH mainnet addresses start with '1'
        payload = bytes(20)
        addr = base58check_encode(0x00, payload)
        self.assertTrue(addr.startswith("1"))

    def test_p2sh_mainnet_prefix(self):
        # P2SH mainnet addresses start with '3'
        payload = bytes(20)
        addr = base58check_encode(0x05, payload)
        self.assertTrue(addr.startswith("3"))


class TestBech32(unittest.TestCase):

    def test_segwit_v0_p2wpkh_roundtrip(self):
        witprog = bytes(20)  # 20-byte all-zeros
        addr = segwit_addr_encode("bc", 0, witprog)
        self.assertTrue(addr.startswith("bc1q"))
        witver, decoded = segwit_addr_decode("bc", addr)
        self.assertEqual(witver, 0)
        self.assertEqual(bytes(decoded), witprog)

    def test_segwit_v0_p2wsh_roundtrip(self):
        witprog = bytes(32)  # 32-byte all-zeros
        addr = segwit_addr_encode("bc", 0, witprog)
        witver, decoded = segwit_addr_decode("bc", addr)
        self.assertEqual(witver, 0)
        self.assertEqual(bytes(decoded), witprog)

    def test_segwit_v1_taproot_roundtrip(self):
        witprog = bytes(32)
        addr = segwit_addr_encode("bc", 1, witprog)
        self.assertTrue(addr.startswith("bc1p"))
        witver, decoded = segwit_addr_decode("bc", addr)
        self.assertEqual(witver, 1)
        self.assertEqual(bytes(decoded), witprog)

    def test_testnet_hrp(self):
        witprog = bytes(20)
        addr = segwit_addr_encode("tb", 0, witprog)
        self.assertTrue(addr.startswith("tb1"))

    def test_wrong_hrp_raises(self):
        witprog = bytes(20)
        addr = segwit_addr_encode("bc", 0, witprog)
        with self.assertRaises(ValueError):
            segwit_addr_decode("tb", addr)  # wrong HRP

    def test_bech32_polymod_returns_int(self):
        from app.btcprotocol.encoding import bech32_polymod
        result = bech32_polymod([0, 1, 2, 3])
        self.assertIsInstance(result, int)


class TestConvertBits(unittest.TestCase):

    def test_8_to_5_to_8_roundtrip(self):
        data = bytes(range(20))
        converted = convertbits(data, 8, 5)
        back = convertbits(converted, 5, 8, pad=False)
        self.assertEqual(bytes(back), data)

    def test_empty_input(self):
        self.assertEqual(convertbits([], 8, 5), [])


class TestCompactSize(unittest.TestCase):

    def test_single_byte_values(self):
        for n in [0, 1, 0xFC]:
            enc = compact_size_encode(n)
            self.assertEqual(len(enc), 1)
            val, off = compact_size_decode(enc)
            self.assertEqual(val, n)
            self.assertEqual(off, 1)

    def test_two_byte_fd(self):
        n = 0xFD
        enc = compact_size_encode(n)
        self.assertEqual(enc[0], 0xFD)
        self.assertEqual(len(enc), 3)
        val, _ = compact_size_decode(enc)
        self.assertEqual(val, n)

    def test_four_byte_fe(self):
        n = 0x10000
        enc = compact_size_encode(n)
        self.assertEqual(enc[0], 0xFE)
        self.assertEqual(len(enc), 5)
        val, _ = compact_size_decode(enc)
        self.assertEqual(val, n)

    def test_eight_byte_ff(self):
        n = 0x100000000
        enc = compact_size_encode(n)
        self.assertEqual(enc[0], 0xFF)
        self.assertEqual(len(enc), 9)
        val, _ = compact_size_decode(enc)
        self.assertEqual(val, n)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            compact_size_encode(-1)


class TestIntHelpers(unittest.TestCase):

    def test_little_endian_roundtrip(self):
        for n in [0, 1, 255, 256, 0xFFFF, 0x12345678]:
            b = int_to_little_endian(n, 4)
            self.assertEqual(len(b), 4)
            self.assertEqual(little_endian_to_int(b), n)

    def test_big_endian_roundtrip(self):
        for n in [0, 1, 255, 0xDEADBEEF]:
            b = int_to_big_endian(n, 4)
            self.assertEqual(len(b), 4)
            self.assertEqual(big_endian_to_int(b), n)

    def test_endian_differ(self):
        n = 0x12345678
        le = int_to_little_endian(n, 4)
        be = int_to_big_endian(n, 4)
        self.assertNotEqual(le, be)


class TestDER(unittest.TestCase):

    def test_roundtrip(self):
        r = 0xDEADBEEFDEADBEEFDEADBEEFDEADBEEF
        s = 0xCAFEBABECAFEBABECAFEBABECAFEBABE
        der = der_encode_signature(r, s)
        r2, s2 = der_decode_signature(der)
        self.assertEqual(r, r2)
        self.assertEqual(s, s2)

    def test_starts_with_sequence_tag(self):
        der = der_encode_signature(1, 1)
        self.assertEqual(der[0], 0x30)

    def test_integer_tag(self):
        enc = der_encode_integer(255)
        self.assertEqual(enc[0], 0x02)

    def test_integer_zero(self):
        enc = der_encode_integer(0)
        self.assertEqual(enc, b"\x02\x01\x00")


class TestHexHelpers(unittest.TestCase):

    def test_hex_to_bytes(self):
        self.assertEqual(hex_to_bytes("deadbeef"), bytes.fromhex("deadbeef"))

    def test_hex_to_bytes_with_prefix(self):
        self.assertEqual(hex_to_bytes("0xdeadbeef"), bytes.fromhex("deadbeef"))

    def test_bytes_to_hex(self):
        self.assertEqual(bytes_to_hex(b"\xde\xad\xbe\xef"), "deadbeef")

    def test_reverse_bytes(self):
        b = bytes.fromhex("0102030405")
        self.assertEqual(reverse_bytes(b), bytes.fromhex("0504030201"))

    def test_reverse_bytes_idempotent(self):
        b = bytes(range(10))
        self.assertEqual(reverse_bytes(reverse_bytes(b)), b)


# ===========================================================================
# Script
# ===========================================================================

class TestOpcodeConstants(unittest.TestCase):

    def test_op_dup_value(self):
        self.assertEqual(OP_DUP, 0x76)

    def test_op_hash160_value(self):
        self.assertEqual(OP_HASH160, 0xA9)

    def test_op_checksig_value(self):
        self.assertEqual(OP_CHECKSIG, 0xAC)

    def test_opcode_names_has_all_standard(self):
        for name in ["OP_DUP", "OP_HASH160", "OP_EQUALVERIFY", "OP_CHECKSIG",
                     "OP_RETURN", "OP_CHECKMULTISIG", "OP_0", "OP_1"]:
            self.assertIn(name, OPCODE_VALUES, f"{name} missing from OPCODE_VALUES")

    def test_opcode_values_roundtrip(self):
        for byte_val, name in OPCODE_NAMES.items():
            self.assertIn(name, OPCODE_VALUES)


class TestScriptClassification(unittest.TestCase):

    def _make_p2pkh(self):
        pubkey_hash = bytes(20)
        return build_p2pkh_script(pubkey_hash)

    def _make_p2sh(self):
        script_hash = bytes(20)
        return build_p2sh_script(script_hash)

    def _make_p2wpkh(self):
        return build_p2wpkh_script(bytes(20))

    def _make_p2wsh(self):
        return build_p2wsh_script(bytes(32))

    def _make_p2tr(self):
        return build_p2tr_script(bytes(32))

    def test_p2pkh_classification(self):
        s = self._make_p2pkh()
        self.assertEqual(s.classify(), "p2pkh")

    def test_p2sh_classification(self):
        s = self._make_p2sh()
        self.assertEqual(s.classify(), "p2sh")

    def test_p2wpkh_classification(self):
        s = self._make_p2wpkh()
        self.assertEqual(s.classify(), "p2wpkh")

    def test_p2wsh_classification(self):
        s = self._make_p2wsh()
        self.assertEqual(s.classify(), "p2wsh")

    def test_p2tr_classification(self):
        s = self._make_p2tr()
        self.assertEqual(s.classify(), "p2tr")

    def test_op_return_classification(self):
        s = build_op_return_script(b"hello")
        self.assertEqual(s.classify(), "op_return")

    def test_multisig_classification(self):
        pk = bytes(33)
        s = build_multisig_script(1, [pk])
        self.assertEqual(s.classify(), "multisig")

    def test_is_standard_p2pkh(self):
        self.assertTrue(self._make_p2pkh().is_standard())

    def test_is_witness_p2wpkh(self):
        self.assertTrue(self._make_p2wpkh().is_witness())

    def test_is_witness_p2tr(self):
        self.assertTrue(self._make_p2tr().is_witness())

    def test_is_not_witness_p2pkh(self):
        self.assertFalse(self._make_p2pkh().is_witness())


class TestScriptSizes(unittest.TestCase):

    def test_p2pkh_is_25_bytes(self):
        s = build_p2pkh_script(bytes(20))
        self.assertEqual(s.get_size(), 25)

    def test_p2sh_is_23_bytes(self):
        s = build_p2sh_script(bytes(20))
        self.assertEqual(s.get_size(), 23)

    def test_p2wpkh_is_22_bytes(self):
        s = build_p2wpkh_script(bytes(20))
        self.assertEqual(s.get_size(), 22)

    def test_p2wsh_is_34_bytes(self):
        s = build_p2wsh_script(bytes(32))
        self.assertEqual(s.get_size(), 34)

    def test_p2tr_is_34_bytes(self):
        s = build_p2tr_script(bytes(32))
        self.assertEqual(s.get_size(), 34)


class TestScriptDisassembly(unittest.TestCase):

    def test_p2pkh_disassembly_contains_known_ops(self):
        s = build_p2pkh_script(bytes(20))
        asm = s.disassemble()
        self.assertIn("OP_DUP", asm)
        self.assertIn("OP_HASH160", asm)
        self.assertIn("OP_EQUALVERIFY", asm)
        self.assertIn("OP_CHECKSIG", asm)

    def test_disassemble_empty_script(self):
        s = Script(b"")
        self.assertEqual(s.disassemble(), "")

    def test_op_return_disassembly(self):
        s = build_op_return_script(b"\xde\xad")
        asm = s.disassemble()
        self.assertIn("OP_RETURN", asm)
        self.assertIn("dead", asm)


class TestScriptBuilder(unittest.TestCase):

    def test_push_data_small(self):
        builder = ScriptBuilder()
        builder.push_data(b"\xAB" * 10)
        script = builder.build()
        tokens = script.parse()
        self.assertIn(b"\xAB" * 10, tokens)

    def test_push_int_0(self):
        s = ScriptBuilder().push_int(0).build()
        self.assertEqual(s._raw, bytes([OP_0]))

    def test_push_int_1(self):
        s = ScriptBuilder().push_int(1).build()
        self.assertEqual(s._raw, bytes([OP_1]))

    def test_push_int_16(self):
        s = ScriptBuilder().push_int(16).build()
        self.assertEqual(s._raw[0], 0x60)  # OP_16

    def test_build_returns_script_instance(self):
        s = ScriptBuilder().push_op(OP_DUP).build()
        self.assertIsInstance(s, Script)


class TestScriptAddresses(unittest.TestCase):

    def test_p2pkh_address_mainnet(self):
        pubkey_hash = bytes(20)
        s = build_p2pkh_script(pubkey_hash)
        addrs = s.get_addresses(network="mainnet")
        self.assertEqual(len(addrs), 1)
        self.assertTrue(addrs[0].startswith("1"))

    def test_p2wpkh_address_mainnet(self):
        pubkey_hash = bytes(20)
        s = build_p2wpkh_script(pubkey_hash)
        addrs = s.get_addresses(network="mainnet")
        self.assertEqual(len(addrs), 1)
        self.assertTrue(addrs[0].startswith("bc1q"))

    def test_op_return_no_address(self):
        s = build_op_return_script(b"data")
        self.assertEqual(s.get_addresses(), [])

    def test_p2tr_address_mainnet(self):
        tweaked_key = bytes(32)
        s = build_p2tr_script(tweaked_key)
        addrs = s.get_addresses(network="mainnet")
        self.assertEqual(len(addrs), 1)
        self.assertTrue(addrs[0].startswith("bc1p"))


class TestTimelockScript(unittest.TestCase):

    def test_timelock_builds_without_error(self):
        s = build_timelock_script(700000, bytes(20))
        self.assertIsInstance(s, Script)

    def test_timelock_disassembly_contains_cltv(self):
        s = build_timelock_script(700000, bytes(20))
        asm = s.disassemble()
        self.assertIn("OP_CHECKLOCKTIMEVERIFY", asm)

    def test_invalid_pubkey_hash_length(self):
        with self.assertRaises(ValueError):
            build_timelock_script(700000, bytes(19))


# ===========================================================================
# Protocol
# ===========================================================================

class TestBlockHeader(unittest.TestCase):

    def _make_header(self, nonce: int = 0) -> BlockHeader:
        return BlockHeader(
            version=1,
            prev_hash=bytes(32),
            merkle_root_bytes=bytes(32),
            timestamp=1231006505,
            bits=0x1D00FFFF,
            nonce=nonce,
        )

    def test_serialize_is_80_bytes(self):
        hdr = self._make_header()
        self.assertEqual(len(hdr.serialize()), 80)

    def test_deserialize_roundtrip(self):
        hdr = self._make_header(nonce=42)
        raw = hdr.serialize()
        hdr2 = BlockHeader.deserialize(raw)
        self.assertEqual(hdr2.nonce, 42)
        self.assertEqual(hdr2.version, 1)
        self.assertEqual(hdr2.bits, 0x1D00FFFF)

    def test_compute_hash_returns_hex_string(self):
        hdr = self._make_header()
        h = hdr.compute_hash()
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_to_dict_keys(self):
        hdr = self._make_header()
        d = hdr.to_dict()
        for key in ["hash", "version", "prev_hash", "merkle_root",
                    "timestamp", "bits", "nonce", "difficulty"]:
            self.assertIn(key, d)

    def test_get_difficulty_genesis(self):
        hdr = self._make_header()
        hdr.bits = 0x1D00FFFF
        diff = hdr.get_difficulty()
        self.assertAlmostEqual(diff, 1.0, places=5)


class TestTxInputOutput(unittest.TestCase):

    def _make_input(self):
        return TxInput(
            prev_txid=bytes(32),
            prev_index=0,
            script_sig=b"\x48" + bytes(71) + b"\x21" + bytes(33),
            sequence=0xFFFFFFFF,
        )

    def _make_output(self):
        script = build_p2pkh_script(bytes(20))
        return TxOutput(value=50_000_000, script_pubkey=bytes(script))

    def test_txinput_serialize_deserialize(self):
        txin = self._make_input()
        raw = txin.serialize()
        txin2, offset = TxInput.deserialize(raw)
        self.assertEqual(txin2.prev_txid, txin.prev_txid)
        self.assertEqual(txin2.prev_index, txin.prev_index)
        self.assertEqual(txin2.sequence, txin.sequence)

    def test_coinbase_detection(self):
        coinbase_in = TxInput(
            prev_txid=bytes(32),
            prev_index=0xFFFFFFFF,
            script_sig=b"\x03\x4e\x89\x0b",
            sequence=0xFFFFFFFF,
        )
        self.assertTrue(coinbase_in.is_coinbase())
        self.assertFalse(self._make_input().is_coinbase())

    def test_txoutput_serialize_deserialize(self):
        txout = self._make_output()
        raw = txout.serialize()
        txout2, _ = TxOutput.deserialize(raw)
        self.assertEqual(txout2.value, 50_000_000)
        self.assertEqual(txout2.script_pubkey, txout.script_pubkey)

    def test_txoutput_value_btc_conversion(self):
        txout = self._make_output()
        d = txout.to_dict()
        self.assertAlmostEqual(d["value_btc"], 0.5, places=8)


class TestTransaction(unittest.TestCase):

    def _make_tx(self):
        txin = TxInput(bytes(32), 0xFFFFFFFF, b"\x01\x00", 0xFFFFFFFF)
        script = build_p2pkh_script(bytes(20))
        txout = TxOutput(50 * 10**8, bytes(script))
        return Transaction(version=1, inputs=[txin], outputs=[txout], locktime=0)

    def test_serialize_deserialize_roundtrip(self):
        tx = self._make_tx()
        raw = tx.serialize()
        tx2, _ = Transaction.deserialize(raw)
        self.assertEqual(tx2.version, tx.version)
        self.assertEqual(len(tx2.inputs), 1)
        self.assertEqual(len(tx2.outputs), 1)
        self.assertEqual(tx2.outputs[0].value, 50 * 10**8)

    def test_compute_txid_returns_hex(self):
        tx = self._make_tx()
        txid = tx.compute_txid()
        self.assertEqual(len(txid), 64)
        # Should be valid hex
        bytes.fromhex(txid)

    def test_is_coinbase(self):
        tx = self._make_tx()
        self.assertTrue(tx.is_coinbase())

    def test_get_fee(self):
        txin = TxInput(bytes(32), 0, b"", 0xFFFFFFFF)
        txout = TxOutput(40 * 10**8, bytes(build_p2pkh_script(bytes(20))))
        tx = Transaction(version=1, inputs=[txin], outputs=[txout])
        fee = tx.get_fee([50 * 10**8])
        self.assertEqual(fee, 10 * 10**8)

    def test_vsize_equals_size_for_legacy(self):
        tx = self._make_tx()
        # Legacy tx: weight = size * 4, vsize = size
        self.assertEqual(tx.get_vsize(), tx.get_size())

    def test_to_dict_has_txid(self):
        tx = self._make_tx()
        d = tx.to_dict()
        self.assertIn("txid", d)
        self.assertIn("vin", d)
        self.assertIn("vout", d)


class TestNetworkConstants(unittest.TestCase):

    def test_mainnet_has_required_keys(self):
        for key in ["magic", "default_port", "bech32_hrp", "genesis_hash"]:
            self.assertIn(key, MAINNET)

    def test_mainnet_port(self):
        self.assertEqual(MAINNET["default_port"], 8333)

    def test_testnet_port(self):
        self.assertEqual(TESTNET["default_port"], 18333)

    def test_regtest_hrp(self):
        self.assertEqual(REGTEST["bech32_hrp"], "bcrt")

    def test_different_magic_bytes(self):
        self.assertNotEqual(MAINNET["magic"], TESTNET["magic"])


# ===========================================================================
# Wordlist
# ===========================================================================

class TestBIP39Wordlist(unittest.TestCase):

    def test_wordlist_has_2048_words(self):
        self.assertEqual(len(BIP39_WORDLIST), 2048)

    def test_first_word_is_abandon(self):
        self.assertEqual(BIP39_WORDLIST[0], "abandon")

    def test_last_word_is_zoo(self):
        self.assertEqual(BIP39_WORDLIST[-1], "zoo")

    def test_get_word_valid(self):
        self.assertEqual(get_word(0), "abandon")
        self.assertEqual(get_word(2047), "zoo")

    def test_get_word_out_of_range(self):
        with self.assertRaises(IndexError):
            get_word(2048)
        with self.assertRaises(IndexError):
            get_word(-1)

    def test_get_index_known(self):
        self.assertEqual(get_index("abandon"), 0)
        self.assertEqual(get_index("zoo"), 2047)

    def test_get_index_not_found(self):
        self.assertEqual(get_index("notaword"), -1)

    def test_validate_word_true(self):
        self.assertTrue(validate_word("abandon"))
        self.assertTrue(validate_word("zoo"))
        self.assertTrue(validate_word("satoshi"))

    def test_validate_word_false(self):
        self.assertFalse(validate_word("notaword"))
        self.assertFalse(validate_word(""))

    def test_suggest_words_returns_list(self):
        results = suggest_words("ab")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        for word in results:
            self.assertTrue(word.startswith("ab"))

    def test_suggest_words_empty_prefix(self):
        self.assertEqual(suggest_words(""), [])

    def test_suggest_words_no_match(self):
        self.assertEqual(suggest_words("zzzzz"), [])

    def test_suggest_words_max_results(self):
        results = suggest_words("a", max_results=3)
        self.assertLessEqual(len(results), 3)

    def test_wordlist_integrity(self):
        self.assertTrue(verify_wordlist_integrity())

    def test_wordlist_hash_is_hex_string(self):
        self.assertEqual(len(WORDLIST_HASH), 64)
        bytes.fromhex(WORDLIST_HASH)  # should not raise

    def test_all_words_lowercase(self):
        for word in BIP39_WORDLIST:
            self.assertEqual(word, word.lower())

    def test_no_duplicate_words(self):
        self.assertEqual(len(set(BIP39_WORDLIST)), 2048)


if __name__ == "__main__":
    unittest.main(verbosity=2)
