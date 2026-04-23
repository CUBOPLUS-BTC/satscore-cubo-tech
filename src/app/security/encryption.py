"""
Encryption utilities for Magma Bitcoin app.
Pure Python stdlib — hashlib, hmac, secrets, base64, struct.
No third-party cryptography libraries required.

SECURITY NOTE:
  The XOR-based stream cipher implemented here is NOT AES and should NOT
  be used for high-security production encryption of financial data.
  For production, replace with a proper AES-GCM implementation backed by
  the `cryptography` package.  This module demonstrates the correct
  structure and key-derivation approach using only stdlib primitives.
"""

import hashlib
import hmac as _hmac
import secrets
import base64
import struct
import time
import json
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PBKDF2_HASH = "sha256"
_PBKDF2_ITERATIONS = 100_000
_KEY_LENGTH = 32          # 256-bit keys
_SALT_LENGTH = 32         # 256-bit salts
_NONCE_LENGTH = 16        # 128-bit nonce for stream cipher
_MAC_LENGTH = 32          # 256-bit HMAC tag
_API_KEY_LENGTH = 32      # 32 bytes → 64 hex chars
_TOKEN_BYTES = 32


# ---------------------------------------------------------------------------
# AESCipher — XOR stream cipher with PBKDF2-derived key + HMAC authentication
# ---------------------------------------------------------------------------

class AESCipher:
    """
    Symmetric authenticated encryption using a XOR stream cipher with
    PBKDF2-SHA256 key derivation and HMAC-SHA256 authentication tag.

    Wire format (all base64url-encoded)::

        salt(32) | nonce(16) | ciphertext(N) | hmac(32)

    Total overhead per message: 80 bytes + base64 expansion (~107 bytes).
    """

    def __init__(self, key: str) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        self._master_key = key.encode("utf-8")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive a 32-byte encryption key from the master key and salt."""
        return hashlib.pbkdf2_hmac(
            _PBKDF2_HASH,
            self._master_key,
            salt,
            _PBKDF2_ITERATIONS,
            dklen=_KEY_LENGTH,
        )

    @staticmethod
    def _derive_mac_key(enc_key: bytes) -> bytes:
        """Derive a separate MAC key by hashing the encryption key."""
        return hashlib.sha256(b"mac:" + enc_key).digest()

    @staticmethod
    def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
        """
        XOR each data byte with a byte from a SHA-256-based keystream.
        keystream = SHA-256(key || nonce || block_counter) repeated as needed.
        """
        output = bytearray(len(data))
        block_size = 32  # SHA-256 output
        block_idx = 0
        keystream = b""

        for i, byte in enumerate(data):
            if i % block_size == 0:
                counter = struct.pack(">Q", block_idx)
                keystream = hashlib.sha256(key + nonce + counter).digest()
                block_idx += 1
            output[i] = byte ^ keystream[i % block_size]

        return bytes(output)

    @staticmethod
    def _compute_mac(mac_key: bytes, salt: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
        """Compute HMAC-SHA256 over salt || nonce || ciphertext."""
        h = _hmac.new(mac_key, digestmod=hashlib.sha256)
        h.update(salt)
        h.update(nonce)
        h.update(ciphertext)
        return h.digest()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        Returns a base64url-encoded string containing salt, nonce, ciphertext, and MAC.
        """
        if not isinstance(plaintext, str):
            raise TypeError("plaintext must be a string")

        salt = os.urandom(_SALT_LENGTH)
        nonce = os.urandom(_NONCE_LENGTH)

        enc_key = self._derive_key(salt)
        mac_key = self._derive_mac_key(enc_key)

        data = plaintext.encode("utf-8")
        ciphertext = self._xor_stream(data, enc_key, nonce)
        mac = self._compute_mac(mac_key, salt, nonce, ciphertext)

        payload = salt + nonce + ciphertext + mac
        return base64.urlsafe_b64encode(payload).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """
        Decrypt a base64url-encoded ciphertext produced by encrypt().
        Raises ValueError if the MAC verification fails.
        """
        if not isinstance(ciphertext_b64, str):
            raise TypeError("ciphertext must be a string")

        try:
            payload = base64.urlsafe_b64decode(
                ciphertext_b64 + "=" * (4 - len(ciphertext_b64) % 4)
                if len(ciphertext_b64) % 4 else ciphertext_b64
            )
        except Exception as exc:
            raise ValueError(f"Invalid base64 encoding: {exc}") from exc

        min_len = _SALT_LENGTH + _NONCE_LENGTH + _MAC_LENGTH
        if len(payload) < min_len:
            raise ValueError("Payload too short to be valid ciphertext")

        salt = payload[:_SALT_LENGTH]
        nonce = payload[_SALT_LENGTH:_SALT_LENGTH + _NONCE_LENGTH]
        mac = payload[-_MAC_LENGTH:]
        ct = payload[_SALT_LENGTH + _NONCE_LENGTH:-_MAC_LENGTH]

        enc_key = self._derive_key(salt)
        mac_key = self._derive_mac_key(enc_key)

        expected_mac = self._compute_mac(mac_key, salt, nonce, ct)

        # Constant-time comparison to prevent timing attacks
        if not _hmac.compare_digest(expected_mac, mac):
            raise ValueError("MAC verification failed — ciphertext has been tampered with")

        plaintext_bytes = self._xor_stream(ct, enc_key, nonce)
        return plaintext_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# KeyDerivation
# ---------------------------------------------------------------------------

class KeyDerivation:
    """
    Password-based key derivation, password hashing, and secure token generation.
    Uses PBKDF2-HMAC-SHA256 for all key derivation operations.
    """

    # ------------------------------------------------------------------
    # Key derivation
    # ------------------------------------------------------------------

    @staticmethod
    def derive_key(
        password: str,
        salt: bytes,
        iterations: int = _PBKDF2_ITERATIONS,
        length: int = _KEY_LENGTH,
    ) -> bytes:
        """
        Derive a key from a password using PBKDF2-HMAC-SHA256.

        Args:
            password: User-supplied password string.
            salt:     Random salt (should be at least 16 bytes).
            iterations: Number of PBKDF2 iterations (default 100 000).
            length:   Desired key length in bytes (default 32).

        Returns:
            Derived key bytes.
        """
        if not isinstance(password, str):
            raise TypeError("password must be a string")
        if not isinstance(salt, bytes):
            raise TypeError("salt must be bytes")

        return hashlib.pbkdf2_hmac(
            _PBKDF2_HASH,
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=length,
        )

    @staticmethod
    def generate_salt(length: int = _SALT_LENGTH) -> bytes:
        """Generate a cryptographically secure random salt."""
        if length < 8:
            raise ValueError("Salt length must be at least 8 bytes")
        return os.urandom(length)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password for storage using PBKDF2-SHA256 with a random salt.

        Returns a string in the format::

            pbkdf2:sha256:<iterations>:<salt_hex>:<hash_hex>
        """
        if not isinstance(password, str) or not password:
            raise ValueError("password must be a non-empty string")

        salt = KeyDerivation.generate_salt()
        iterations = _PBKDF2_ITERATIONS
        dk = hashlib.pbkdf2_hmac(
            _PBKDF2_HASH,
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return (
            f"pbkdf2:{_PBKDF2_HASH}:{iterations}"
            f":{salt.hex()}:{dk.hex()}"
        )

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a password against a stored PBKDF2 hash string.
        Uses constant-time comparison to prevent timing attacks.
        Returns False (not raises) for malformed hashes.
        """
        if not isinstance(password, str) or not isinstance(hashed, str):
            return False

        try:
            parts = hashed.split(":")
            if len(parts) != 5 or parts[0] != "pbkdf2":
                return False

            _, algo, iterations_str, salt_hex, stored_hex = parts
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            stored = bytes.fromhex(stored_hex)
        except Exception:
            return False

        computed = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt,
            iterations,
        )

        return _hmac.compare_digest(computed, stored)

    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a secure, URL-safe API key.
        Format: ``mk_<32 random bytes as hex>``  (68 chars total)
        """
        raw = secrets.token_bytes(_API_KEY_LENGTH)
        return "mk_" + raw.hex()

    @staticmethod
    def generate_token(length: int = _TOKEN_BYTES) -> str:
        """
        Generate a secure random token as a hexadecimal string.
        length is in bytes; the returned string will be 2*length characters.
        """
        if length < 8:
            raise ValueError("Token length must be at least 8 bytes")
        return secrets.token_hex(length)

    @staticmethod
    def generate_otp(digits: int = 6) -> str:
        """Generate a numeric one-time password of the specified digit count."""
        if not 4 <= digits <= 10:
            raise ValueError("OTP digits must be between 4 and 10")
        max_val = 10 ** digits
        return str(secrets.randbelow(max_val)).zfill(digits)

    @staticmethod
    def fingerprint(data: str) -> str:
        """
        Compute a short SHA-256 fingerprint of arbitrary data.
        Returns the first 16 hex characters (64-bit fingerprint).
        """
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# SecureStore
# ---------------------------------------------------------------------------

class SecureStore:
    """
    In-process encrypted secret store backed by the AESCipher.
    Secrets are stored as encrypted blobs; the store itself is an in-memory
    dict (no disk persistence by default).  For production, persist the
    encrypted blobs to a database column.
    """

    def __init__(self, master_key: str) -> None:
        if not isinstance(master_key, str) or not master_key:
            raise ValueError("master_key must be a non-empty string")
        self._cipher = AESCipher(master_key)
        self._store: dict[str, str] = {}  # key → encrypted blob

    # ------------------------------------------------------------------
    # Storage operations
    # ------------------------------------------------------------------

    def store_secret(self, key: str, value: str) -> str:
        """
        Encrypt ``value`` and store it under ``key``.
        Returns the encrypted blob (can be persisted externally).
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")

        encrypted = self._cipher.encrypt(value)
        self._store[key] = encrypted
        return encrypted

    def retrieve_secret(self, key: str, encrypted: Optional[str] = None) -> str:
        """
        Decrypt and return the secret stored under ``key``.

        If ``encrypted`` is provided it is used directly (for retrieving
        externally-persisted blobs).  Otherwise the internal store is
        consulted.

        Raises KeyError if the key is not found.
        Raises ValueError if decryption fails.
        """
        if encrypted is not None:
            return self._cipher.decrypt(encrypted)

        if key not in self._store:
            raise KeyError(f"No secret stored for key: {key!r}")

        return self._cipher.decrypt(self._store[key])

    def delete_secret(self, key: str) -> bool:
        """Remove a secret from the store. Returns True if it existed."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def list_keys(self) -> list:
        """Return a list of all stored key names (not their values)."""
        return list(self._store.keys())

    def rotate_key(self, old_key: str, new_key: str, data: dict) -> dict:
        """
        Re-encrypt all secrets in ``data`` from ``old_key`` to ``new_key``.

        ``data`` is a dict mapping secret_name → encrypted_blob (as returned
        by store_secret).  Returns a new dict with the same keys but blobs
        re-encrypted under the new master key.

        The old and new master keys are the *cipher* master keys, not the
        secret names.
        """
        old_cipher = AESCipher(old_key)
        new_cipher = AESCipher(new_key)

        rotated: dict = {}
        errors: list = []

        for name, encrypted_blob in data.items():
            try:
                plaintext = old_cipher.decrypt(encrypted_blob)
                rotated[name] = new_cipher.encrypt(plaintext)
            except Exception as exc:
                errors.append({"name": name, "error": str(exc)})

        return {"rotated": rotated, "errors": errors, "count": len(rotated)}

    def export_encrypted(self) -> dict:
        """Export the entire store as a dict of encrypted blobs."""
        return dict(self._store)

    def import_encrypted(self, data: dict) -> int:
        """Import encrypted blobs into the store. Returns count imported."""
        count = 0
        for key, blob in data.items():
            if isinstance(key, str) and isinstance(blob, str):
                self._store[key] = blob
                count += 1
        return count


# ---------------------------------------------------------------------------
# SignatureManager
# ---------------------------------------------------------------------------

class SignatureManager:
    """
    HMAC-SHA256 based request signing and verification.
    Used for authenticating API requests without passwords.

    Signing scheme::

        signature = HMAC-SHA256(
            key,
            METHOD\nPATH\nBODY_HASH\nTIMESTAMP
        )

    where BODY_HASH = SHA-256(body_bytes).hexdigest()
    """

    _SEPARATOR = "\n"
    _DEFAULT_MAX_AGE = 300  # 5 minutes

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Data signing
    # ------------------------------------------------------------------

    def sign_data(self, data: str, key: str) -> str:
        """
        Compute HMAC-SHA256 of ``data`` using ``key``.
        Returns the signature as a hex string.
        """
        if not isinstance(data, str):
            raise TypeError("data must be a string")
        if not isinstance(key, str) or not key:
            raise TypeError("key must be a non-empty string")

        h = _hmac.new(
            key.encode("utf-8"),
            data.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        return h.hexdigest()

    def verify_signature(self, data: str, signature: str, key: str) -> bool:
        """
        Verify an HMAC-SHA256 signature using constant-time comparison.
        Returns False (not raises) on any error.
        """
        if not all(isinstance(x, str) for x in (data, signature, key)):
            return False

        try:
            expected = self.sign_data(data, key)
            return _hmac.compare_digest(expected, signature)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Request signing (canonical form)
    # ------------------------------------------------------------------

    def sign_request(
        self,
        method: str,
        path: str,
        body: str,
        timestamp: int,
        key: str,
    ) -> str:
        """
        Sign an HTTP request using a canonical string representation.

        Canonical string::

            METHOD\nPATH\nSHA256(body)\nTIMESTAMP

        Returns HMAC-SHA256 hex signature.
        """
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        canonical = self._SEPARATOR.join([
            method.upper(),
            path,
            body_hash,
            str(int(timestamp)),
        ])
        return self.sign_data(canonical, key)

    def verify_request(
        self,
        method: str,
        path: str,
        body: str,
        timestamp: int,
        signature: str,
        key: str,
        max_age: int = _DEFAULT_MAX_AGE,
    ) -> bool:
        """
        Verify a signed HTTP request.

        Checks:
        1. Timestamp is within ``max_age`` seconds of now.
        2. HMAC signature matches the canonical form.

        Returns False on any failure.
        """
        try:
            ts = int(timestamp)
            now = int(time.time())

            if abs(now - ts) > max_age:
                return False

            expected = self.sign_request(method, path, body, ts, key)
            return _hmac.compare_digest(expected, signature)
        except Exception:
            return False

    def generate_webhook_secret(self) -> str:
        """Generate a secure webhook signing secret."""
        return "whsec_" + secrets.token_hex(32)

    def sign_webhook_payload(self, payload: str, secret: str, timestamp: int = None) -> str:
        """
        Sign a webhook payload in a format compatible with common webhook patterns.
        Returns ``t=<timestamp>,v1=<signature>``.
        """
        if timestamp is None:
            timestamp = int(time.time())

        signed_content = f"{timestamp}.{payload}"
        sig = self.sign_data(signed_content, secret)
        return f"t={timestamp},v1={sig}"

    def verify_webhook_payload(
        self,
        payload: str,
        header: str,
        secret: str,
        tolerance: int = 300,
    ) -> bool:
        """
        Verify a webhook signature header produced by sign_webhook_payload.
        ``header`` format: ``t=<timestamp>,v1=<signature>``
        Returns False on any failure.
        """
        try:
            parts = dict(item.split("=", 1) for item in header.split(","))
            timestamp = int(parts["t"])
            signature = parts["v1"]

            now = int(time.time())
            if abs(now - timestamp) > tolerance:
                return False

            signed_content = f"{timestamp}.{payload}"
            expected = self.sign_data(signed_content, secret)
            return _hmac.compare_digest(expected, signature)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # JWT-like stateless token (simple, no third-party)
    # ------------------------------------------------------------------

    def create_signed_token(
        self,
        payload: dict,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Create a simple signed token (NOT standard JWT).
        Format (base64url): header.payload.signature
        Uses HMAC-SHA256 for signing.
        """
        header = {"alg": "HS256", "typ": "MagmaToken"}
        payload_with_exp = dict(payload)
        payload_with_exp["iat"] = int(time.time())
        payload_with_exp["exp"] = int(time.time()) + expires_in

        def b64url(data: str) -> str:
            return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()

        header_b64 = b64url(json.dumps(header, separators=(",", ":")))
        payload_b64 = b64url(json.dumps(payload_with_exp, separators=(",", ":")))

        signing_input = f"{header_b64}.{payload_b64}"
        signature = self.sign_data(signing_input, key)
        sig_b64 = base64.urlsafe_b64encode(bytes.fromhex(signature)).rstrip(b"=").decode()

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_signed_token(self, token: str, key: str) -> Optional[dict]:
        """
        Verify and decode a signed token produced by create_signed_token.
        Returns the payload dict if valid, or None if invalid/expired.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            signing_input = f"{header_b64}.{payload_b64}"
            signature_bytes = base64.urlsafe_b64decode(sig_b64 + "==")
            expected_sig = self.sign_data(signing_input, key)

            if not _hmac.compare_digest(bytes.fromhex(expected_sig), signature_bytes):
                return None

            # Decode payload
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())

            # Check expiry
            now = int(time.time())
            if payload.get("exp", 0) < now:
                return None

            return payload
        except Exception:
            return None
