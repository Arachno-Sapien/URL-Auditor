"""
Integration tests for the POST /audit endpoint.

Uses Flask's test client and mocks the requests.get call
so tests don't make real HTTP requests.

Covers:
- Happy path: valid URL + HTML response → 200 with audit data
- Failure: malformed URL → 400
- Failure: non-HTML content-type → 422
"""

import pytest
from unittest.mock import patch, MagicMock

from app import create_app


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary database."""
    import os
    os.environ["AUDITOR_DB_PATH"] = str(tmp_path / "test_audits.db")
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Helper to build a mock requests.Response ---

def _mock_response(status_code=200, content_type="text/html; charset=utf-8", text="", elapsed_seconds=0.3):
    """Build a mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"Content-Type": content_type}
    mock_resp.text = text
    mock_resp.elapsed.total_seconds.return_value = elapsed_seconds
    mock_resp.close = MagicMock()
    return mock_resp


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Example Domain</title>
    <meta name="description" content="This domain is for use in illustrative examples.">
</head>
<body>
    <h1>Example Domain</h1>
    <p>This domain is for use in illustrative examples in documents.</p>
    <img src="logo.png" alt="Logo">
    <img src="banner.png">
</body>
</html>
"""


class TestAuditEndpoint:
    """Integration tests for POST /audit."""

    # --- Happy path ---

    @patch("app.fetcher.requests.get")
    def test_valid_url_returns_audit_report(self, mock_get, client):
        """A valid URL with HTML content should return a full audit report."""
        mock_get.return_value = _mock_response(
            status_code=200,
            text=SAMPLE_HTML,
        )

        resp = client.post("/audit", json={"url": "https://example.com"})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["data"]["url"] == "https://example.com"
        assert data["data"]["status_code"] == 200
        assert data["data"]["title"] == "Example Domain"
        assert data["data"]["meta_description"] == "This domain is for use in illustrative examples."
        assert data["data"]["h1_count"] == 1
        assert data["data"]["total_images"] == 2
        assert data["data"]["images_missing_alt"] == 1
        assert data["data"]["word_count"] > 0
        assert "response_time_ms" in data["data"]

    # --- Failure: malformed URL ---

    def test_malformed_url_returns_400(self, client):
        """A malformed URL should return a 400 with a helpful message."""
        resp = client.post("/audit", json={"url": "not-a-url"})
        data = resp.get_json()

        assert resp.status_code == 400
        assert data["success"] is False
        assert "Invalid URL" in data["error"]

    def test_missing_url_returns_400(self, client):
        """Missing URL field should return a 400."""
        resp = client.post("/audit", json={})
        data = resp.get_json()

        assert resp.status_code == 400
        assert data["success"] is False
        assert "required" in data["error"].lower()

    def test_empty_url_returns_400(self, client):
        """Empty URL string should return a 400."""
        resp = client.post("/audit", json={"url": ""})
        data = resp.get_json()

        assert resp.status_code == 400
        assert data["success"] is False

    # --- Failure: non-HTML content-type ---

    @patch("app.fetcher.requests.get")
    def test_non_html_content_type_returns_422(self, mock_get, client):
        """A URL returning non-HTML content (e.g. PDF) should return 422."""
        mock_get.return_value = _mock_response(
            status_code=200,
            content_type="application/pdf",
            text="%PDF-1.4 binary content here",
        )

        resp = client.post("/audit", json={"url": "https://example.com/doc.pdf"})
        data = resp.get_json()

        assert resp.status_code == 422
        assert data["success"] is False
        assert "not an HTML page" in data["error"]

    # --- Failure: timeout ---

    @patch("app.fetcher.requests.get")
    def test_timeout_returns_504(self, mock_get, client):
        """A timeout should return 504 with a clear message."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.Timeout("Connection timed out")

        resp = client.post("/audit", json={"url": "https://slow-site.com"})
        data = resp.get_json()

        assert resp.status_code == 504
        assert data["success"] is False
        assert "too long" in data["error"].lower()

    # --- Failure: DNS / connection error ---

    @patch("app.fetcher.requests.get")
    def test_dns_failure_returns_502(self, mock_get, client):
        """A DNS resolution failure should return 502."""
        import requests as req_lib
        mock_get.side_effect = req_lib.exceptions.ConnectionError(
            "Failed to resolve 'nonexistent.invalid'"
        )

        resp = client.post("/audit", json={"url": "https://nonexistent.invalid"})
        data = resp.get_json()

        assert resp.status_code == 502
        assert data["success"] is False

    # --- Edge: GET on /audit should return 405 ---

    def test_get_audit_returns_405(self, client):
        """GET /audit should return 405 Method Not Allowed."""
        resp = client.get("/audit")
        assert resp.status_code == 405

    # --- CSV Export ---

    @patch("app.fetcher.requests.get")
    def test_csv_export(self, mock_get, client):
        """Should return a CSV file for a previously audited URL."""
        # First do a POST to create an audit record
        mock_get.return_value = _mock_response(
            status_code=200,
            text=SAMPLE_HTML,
        )
        client.post("/audit", json={"url": "https://example.com/csv"})

        # Now test the CSV export
        resp = client.get("/export/csv?url=https://example.com/csv")
        
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers["Content-Disposition"]
        
        text = resp.get_data(as_text=True)
        assert "URL,Status Code,Response Time (ms)" in text
        assert "https://example.com/csv,200" in text

    def test_csv_export_no_url(self, client):
        """CSV export without URL should return 400."""
        resp = client.get("/export/csv")
        assert resp.status_code == 400

    def test_csv_export_not_found(self, client):
        """CSV export for unaudited URL should return 404."""
        resp = client.get("/export/csv?url=https://never-audited.com")
        assert resp.status_code == 404
