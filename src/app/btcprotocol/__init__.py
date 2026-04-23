"""
app.btcprotocol - Bitcoin cryptographic primitives.

Submodules
----------
hashing   : SHA-256, RIPEMD-160, HMAC-SHA-512, Merkle trees, tagged hash,
            block hash, difficulty target, and work calculation
encoding  : Base58Check, Bech32/Bech32m, SegWit addresses, CompactSize,
            DER encoding, and integer/hex helpers
script    : Bitcoin Script opcodes, Script class (parse/classify/disassemble),
            ScriptBuilder, and template builders
protocol  : BlockHeader, Transaction, TxInput, TxOutput, Block classes;
            network configuration constants (MAINNET, TESTNET, SIGNET, REGTEST)
wordlist  : Complete BIP-39 English wordlist with lookup and autocomplete helpers
"""

from .hashing import (
    sha256,
    double_sha256,
    ripemd160,
    hash160,
    hmac_sha512,
    pbkdf2_hmac_sha512,
    tagged_hash,
    merkle_root,
    merkle_proof,
    verify_merkle_proof,
    checksum,
    compute_txid,
    compute_wtxid,
    compute_block_hash,
    compute_target,
    difficulty_from_target,
    work_from_target,
)

from .encoding import (
    base58_alphabet,
    base58_encode,
    base58_decode,
    base58check_encode,
    base58check_decode,
    bech32_charset,
    bech32_polymod,
    bech32_hrp_expand,
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
    der_encode_integer,
    der_encode_signature,
    der_decode_signature,
    hex_to_bytes,
    bytes_to_hex,
    reverse_bytes,
    # backward-compatible aliases
    compact_size,
    read_compact_size,
)

from .script import (
    # Individual opcode constants
    OP_0, OP_FALSE, OP_PUSHDATA1, OP_PUSHDATA2, OP_PUSHDATA4,
    OP_1NEGATE, OP_RESERVED, OP_1, OP_TRUE, OP_2, OP_3, OP_4, OP_5, OP_6,
    OP_7, OP_8, OP_9, OP_10, OP_11, OP_12, OP_13, OP_14, OP_15, OP_16,
    OP_NOP, OP_VER, OP_IF, OP_NOTIF, OP_VERIF, OP_VERNOTIF,
    OP_ELSE, OP_ENDIF, OP_VERIFY, OP_RETURN,
    OP_TOALTSTACK, OP_FROMALTSTACK, OP_IFDUP, OP_DEPTH,
    OP_DROP, OP_DUP, OP_NIP, OP_OVER, OP_PICK, OP_ROLL,
    OP_ROT, OP_SWAP, OP_TUCK,
    OP_2DROP, OP_2DUP, OP_3DUP, OP_2OVER, OP_2ROT, OP_2SWAP,
    OP_SIZE, OP_EQUAL, OP_EQUALVERIFY,
    OP_1ADD, OP_1SUB, OP_NEGATE, OP_ABS, OP_NOT, OP_0NOTEQUAL,
    OP_ADD, OP_SUB, OP_BOOLAND, OP_BOOLOR,
    OP_NUMEQUAL, OP_NUMEQUALVERIFY, OP_NUMNOTEQUAL,
    OP_LESSTHAN, OP_GREATERTHAN, OP_LESSTHANOREQUAL, OP_GREATERTHANOREQUAL,
    OP_MIN, OP_MAX, OP_WITHIN,
    OP_RIPEMD160, OP_SHA1, OP_SHA256, OP_HASH160, OP_HASH256,
    OP_CODESEPARATOR, OP_CHECKSIG, OP_CHECKSIGVERIFY,
    OP_CHECKMULTISIG, OP_CHECKMULTISIGVERIFY,
    OP_CHECKSIGADD,
    OP_CHECKLOCKTIMEVERIFY, OP_CHECKSEQUENCEVERIFY,
    OP_NOP1, OP_NOP4, OP_NOP5, OP_NOP6, OP_NOP7, OP_NOP8, OP_NOP9, OP_NOP10,
    OP_PUBKEYHASH, OP_PUBKEY, OP_INVALIDOPCODE,
    # Lookup dicts
    OPCODE_NAMES,
    OPCODE_VALUES,
    OPCODES,
    # Classes
    Script,
    ScriptBuilder,
    # Template builders
    build_p2pkh_script,
    build_p2sh_script,
    build_p2wpkh_script,
    build_p2wsh_script,
    build_p2tr_script,
    build_multisig_script,
    build_op_return_script,
    build_timelock_script,
    # Functional API
    parse_script,
    classify_script,
    extract_addresses,
    is_standard,
    estimate_script_size,
    disassemble,
)

from .protocol import (
    MAINNET,
    TESTNET,
    SIGNET,
    REGTEST,
    BlockHeader,
    TxInput,
    TxOutput,
    Transaction,
    Block,
)

from .wordlist import (
    BIP39_WORDLIST,
    WORDLIST_HASH,
    get_word,
    get_index,
    suggest_words,
    validate_word,
    verify_wordlist_integrity,
)

__all__ = [
    # hashing
    "sha256", "double_sha256", "ripemd160", "hash160",
    "hmac_sha512", "pbkdf2_hmac_sha512", "tagged_hash",
    "merkle_root", "merkle_proof", "verify_merkle_proof", "checksum",
    "compute_txid", "compute_wtxid", "compute_block_hash",
    "compute_target", "difficulty_from_target", "work_from_target",
    # encoding
    "base58_alphabet", "base58_encode", "base58_decode",
    "base58check_encode", "base58check_decode",
    "bech32_charset", "bech32_polymod", "bech32_hrp_expand",
    "bech32_encode", "bech32_decode", "bech32m_encode", "bech32m_decode",
    "convertbits", "segwit_addr_encode", "segwit_addr_decode",
    "compact_size_encode", "compact_size_decode",
    "int_to_little_endian", "little_endian_to_int",
    "int_to_big_endian", "big_endian_to_int",
    "der_encode_integer", "der_encode_signature", "der_decode_signature",
    "hex_to_bytes", "bytes_to_hex", "reverse_bytes",
    "compact_size", "read_compact_size",
    # script opcodes
    "OP_0", "OP_FALSE", "OP_1", "OP_TRUE", "OP_RETURN",
    "OP_DUP", "OP_HASH160", "OP_EQUAL", "OP_EQUALVERIFY",
    "OP_CHECKSIG", "OP_CHECKMULTISIG", "OP_CHECKSIGADD",
    "OP_CHECKLOCKTIMEVERIFY", "OP_CHECKSEQUENCEVERIFY",
    "OPCODE_NAMES", "OPCODE_VALUES", "OPCODES",
    # script classes / builders
    "Script", "ScriptBuilder",
    "build_p2pkh_script", "build_p2sh_script",
    "build_p2wpkh_script", "build_p2wsh_script",
    "build_p2tr_script", "build_multisig_script",
    "build_op_return_script", "build_timelock_script",
    "parse_script", "classify_script", "extract_addresses",
    "is_standard", "estimate_script_size", "disassemble",
    # protocol
    "MAINNET", "TESTNET", "SIGNET", "REGTEST",
    "BlockHeader", "TxInput", "TxOutput", "Transaction", "Block",
    # wordlist
    "BIP39_WORDLIST", "WORDLIST_HASH",
    "get_word", "get_index", "suggest_words", "validate_word",
    "verify_wordlist_integrity",
]
