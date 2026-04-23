"""Tests for app/validation.py

Covers:
- validate_pubkey: valid/invalid hex pubkeys
- validate_amount: numeric range edge cases
- validate_string: length and empty-string handling
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.validation import validate_pubkey, validate_amount, validate_string


class TestValidatePubkey(unittest.TestCase):
    """Tests for validate_pubkey."""

    # --- valid cases ---

    def test_valid_all_lowercase(self):
        key = "a" * 64
        self.assertTrue(validate_pubkey(key))

    def test_valid_all_uppercase(self):
        key = "A" * 64
        self.assertTrue(validate_pubkey(key))

    def test_valid_mixed_case(self):
        key = ("aAbBcCdD" * 8)[:64]
        self.assertTrue(validate_pubkey(key))

    def test_valid_all_digits(self):
        key = "1234567890" * 6 + "1234"
        self.assertEqual(len(key), 64)
        self.assertTrue(validate_pubkey(key))

    def test_valid_realistic_pubkey(self):
        key = "02" + "f" * 62  # looks like a compressed pubkey hex without the 33-byte limit
        self.assertTrue(validate_pubkey(key))

    def test_valid_zero_filled(self):
        key = "0" * 64
        self.assertTrue(validate_pubkey(key))

    def test_valid_fe_filled(self):
        key = "fe" * 32
        self.assertEqual(len(key), 64)
        self.assertTrue(validate_pubkey(key))

    # --- invalid: length ---

    def test_invalid_too_short(self):
        self.assertFalse(validate_pubkey("a" * 63))

    def test_invalid_too_long(self):
        self.assertFalse(validate_pubkey("a" * 65))

    def test_invalid_empty_string(self):
        self.assertFalse(validate_pubkey(""))

    def test_invalid_32_chars(self):
        self.assertFalse(validate_pubkey("a" * 32))

    # --- invalid: characters ---

    def test_invalid_contains_space(self):
        key = "a" * 32 + " " + "a" * 31
        self.assertFalse(validate_pubkey(key))

    def test_invalid_contains_g(self):
        key = "g" + "a" * 63
        self.assertFalse(validate_pubkey(key))

    def test_invalid_contains_special_char(self):
        key = "a" * 63 + "@"
        self.assertFalse(validate_pubkey(key))

    def test_invalid_unicode(self):
        key = "ñ" * 64
        self.assertFalse(validate_pubkey(key))

    def test_invalid_newline_in_key(self):
        key = "a" * 63 + "\n"
        self.assertFalse(validate_pubkey(key))


class TestValidateAmount(unittest.TestCase):
    """Tests for validate_amount."""

    # --- within defaults (0 – 1_000_000) ---

    def test_valid_zero(self):
        self.assertTrue(validate_amount(0))

    def test_valid_positive(self):
        self.assertTrue(validate_amount(100))

    def test_valid_max_boundary(self):
        self.assertTrue(validate_amount(1_000_000))

    def test_valid_float(self):
        self.assertTrue(validate_amount(99.99))

    def test_valid_small_satoshi(self):
        self.assertTrue(validate_amount(0.00000001))

    # --- custom min / max ---

    def test_valid_with_custom_min(self):
        self.assertTrue(validate_amount(10, min_val=10))

    def test_valid_with_custom_max(self):
        self.assertTrue(validate_amount(5000, max_val=5000))

    def test_invalid_below_custom_min(self):
        self.assertFalse(validate_amount(9.99, min_val=10))

    def test_invalid_above_custom_max(self):
        self.assertFalse(validate_amount(5001, max_val=5000))

    # --- out of default range ---

    def test_invalid_negative(self):
        self.assertFalse(validate_amount(-1))

    def test_invalid_above_max(self):
        self.assertFalse(validate_amount(1_000_001))

    def test_invalid_large_negative(self):
        self.assertFalse(validate_amount(-99999))

    def test_boundary_just_below_zero(self):
        self.assertFalse(validate_amount(-0.00000001))

    def test_boundary_just_above_max(self):
        self.assertFalse(validate_amount(1_000_000.01))


class TestValidateString(unittest.TestCase):
    """Tests for validate_string."""

    # --- valid ---

    def test_valid_normal_string(self):
        self.assertTrue(validate_string("hello"))

    def test_valid_exactly_max_len(self):
        self.assertTrue(validate_string("x" * 256))

    def test_valid_single_char(self):
        self.assertTrue(validate_string("a"))

    def test_valid_unicode_within_limit(self):
        self.assertTrue(validate_string("El Salvador 🌋"))

    def test_valid_custom_max_len(self):
        self.assertTrue(validate_string("hello", max_len=10))

    # --- invalid: too long ---

    def test_invalid_one_over_max(self):
        self.assertFalse(validate_string("x" * 257))

    def test_invalid_very_long_string(self):
        self.assertFalse(validate_string("a" * 10_000))

    def test_invalid_custom_max_exceeded(self):
        self.assertFalse(validate_string("toolong", max_len=3))

    # --- invalid: empty / falsy ---

    def test_invalid_empty_string(self):
        self.assertFalse(validate_string(""))

    def test_invalid_none_like_zero(self):
        # validate_string expects a str; falsy check should block whitespace-only?
        # Actually whitespace is truthy — "" is the falsy case.
        self.assertTrue(validate_string("   "))  # spaces are truthy

    def test_boundary_max_len_zero(self):
        # max_len=0 means nothing passes
        self.assertFalse(validate_string("a", max_len=0))

    def test_boundary_exactly_one_over_custom(self):
        self.assertFalse(validate_string("ab", max_len=1))

    def test_valid_numeric_string(self):
        self.assertTrue(validate_string("12345"))

    def test_valid_json_like_string(self):
        self.assertTrue(validate_string('{"key": "value"}'))


if __name__ == "__main__":
    unittest.main()
