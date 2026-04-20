import math

import pytest

from app.validation import (
    validate_amount,
    validate_pubkey,
    validate_string,
    validate_years,
)


class TestValidatePubkey:
    def test_valid_64_hex(self):
        assert validate_pubkey("a" * 64)
        assert validate_pubkey("0123456789abcdef" * 4)
        assert validate_pubkey("ABCDEF" + "0" * 58)

    def test_wrong_length(self):
        assert not validate_pubkey("a" * 63)
        assert not validate_pubkey("a" * 65)
        assert not validate_pubkey("")

    def test_non_hex_chars(self):
        assert not validate_pubkey("g" * 64)
        assert not validate_pubkey(" " * 64)

    def test_non_string_input(self):
        assert not validate_pubkey(None)  # type: ignore[arg-type]
        assert not validate_pubkey(123)  # type: ignore[arg-type]


class TestValidateAmount:
    def test_in_range(self):
        assert validate_amount(0)
        assert validate_amount(100.5)
        assert validate_amount(1_000_000)

    def test_out_of_range(self):
        assert not validate_amount(-1)
        assert not validate_amount(1_000_001)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
    def test_rejects_nonfinite(self, value):
        assert not validate_amount(value)

    def test_rejects_bool(self):
        assert not validate_amount(True)
        assert not validate_amount(False)

    def test_rejects_non_numeric(self):
        assert not validate_amount("100")  # type: ignore[arg-type]
        assert not validate_amount(None)  # type: ignore[arg-type]


class TestValidateYears:
    def test_in_range(self):
        assert validate_years(1)
        assert validate_years(50)

    def test_out_of_range(self):
        assert not validate_years(0)
        assert not validate_years(51)

    def test_rejects_float_and_bool(self):
        assert not validate_years(1.5)  # type: ignore[arg-type]
        assert not validate_years(True)


class TestValidateString:
    def test_valid(self):
        assert validate_string("hello")
        assert validate_string("a" * 256)

    def test_empty_string(self):
        assert not validate_string("")

    def test_too_long(self):
        assert not validate_string("a" * 257)

    def test_non_string(self):
        assert not validate_string(None)  # type: ignore[arg-type]
        assert not validate_string(123)  # type: ignore[arg-type]

    def test_custom_max_len(self):
        assert validate_string("abc", max_len=3)
        assert not validate_string("abcd", max_len=3)
