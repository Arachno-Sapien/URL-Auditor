"""
Tests for app.validator — URL validation logic.

Covers:
- Valid http/https URLs pass through
- Malformed URLs rejected
- Non-http protocols rejected
- Empty/missing input rejected
"""

import pytest
from app.validator import validate_url
from app.errors import ValidationError


class TestValidateUrl:
    """Tests for validate_url function."""

    # --- Happy path ---

    def test_valid_https_url(self):
        result = validate_url("https://example.com")
        assert result == "https://example.com"

    def test_valid_http_url(self):
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_valid_url_with_path(self):
        result = validate_url("https://example.com/page/about")
        assert result == "https://example.com/page/about"

    def test_valid_url_with_query_params(self):
        result = validate_url("https://example.com/search?q=hello&page=1")
        assert result == "https://example.com/search?q=hello&page=1"

    def test_valid_url_with_port(self):
        result = validate_url("http://localhost:3000")
        assert result == "http://localhost:3000"

    def test_strips_whitespace(self):
        result = validate_url("  https://example.com  ")
        assert result == "https://example.com"

    # --- Failure: malformed URLs ---

    def test_rejects_no_protocol(self):
        with pytest.raises(ValidationError):
            validate_url("example.com")

    def test_rejects_garbage_input(self):
        with pytest.raises(ValidationError):
            validate_url("not a url at all")

    def test_rejects_just_protocol(self):
        with pytest.raises(ValidationError):
            validate_url("https://")

    # --- Failure: non-http protocols ---

    def test_rejects_ftp(self):
        with pytest.raises(ValidationError, match="Unsupported protocol"):
            validate_url("ftp://example.com")

    def test_rejects_javascript(self):
        with pytest.raises(ValidationError):
            validate_url("javascript:alert(1)")

    def test_rejects_file_protocol(self):
        # file:// URLs have no netloc, so they fail structural validation
        with pytest.raises(ValidationError):
            validate_url("file:///etc/passwd")

    # --- Failure: empty/missing input ---

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError, match="required"):
            validate_url("")

    def test_rejects_none(self):
        with pytest.raises(ValidationError, match="required"):
            validate_url(None)

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValidationError, match="required"):
            validate_url("   ")

    def test_rejects_non_string(self):
        with pytest.raises(ValidationError, match="required"):
            validate_url(12345)
