from app.auth.bech32 import bech32_encode, lnurl_encode


class TestBech32Encode:
    def test_empty_data(self):
        result = bech32_encode("lnurl", b"")
        assert result.startswith("lnurl1")
        assert len(result) == len("lnurl1") + 6  # 6 checksum chars

    def test_charset_only_lower(self):
        result = bech32_encode("lnurl", b"hello")
        body = result.split("1", 1)[1]
        assert all(c in "qpzry9x8gf2tvdw0s3jn54khce6mua7l" for c in body)

    def test_deterministic(self):
        a = bech32_encode("lnurl", b"https://example.com/lnurl")
        b = bech32_encode("lnurl", b"https://example.com/lnurl")
        assert a == b


class TestLnurlEncode:
    def test_returns_uppercase(self):
        encoded = lnurl_encode("https://example.com")
        assert encoded == encoded.upper()

    def test_hrp_prefix(self):
        encoded = lnurl_encode("https://example.com")
        assert encoded.startswith("LNURL1")

    def test_different_urls_produce_different_output(self):
        a = lnurl_encode("https://example.com/a")
        b = lnurl_encode("https://example.com/b")
        assert a != b

    def test_only_charset_chars(self):
        encoded = lnurl_encode("https://example.com/x?y=1").lower()
        body = encoded.split("1", 1)[1]
        assert all(c in "qpzry9x8gf2tvdw0s3jn54khce6mua7l" for c in body)

    def test_deterministic_roundtrip_length(self):
        url = "https://example.com/callback?k1=" + "a" * 64
        # bech32 length = len(hrp) + 1 + ceil(bits/5) + 6 checksum.
        expected_body = (len(url.encode()) * 8 + 4) // 5
        encoded = lnurl_encode(url)
        assert len(encoded) == len("LNURL1") + expected_body + 6
