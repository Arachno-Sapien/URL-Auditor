"""
Custom exception classes for the URL Auditor.

Each exception carries a user-friendly message and an HTTP status code,
so the route handler can map errors to responses without a big if/else chain.
"""


class ValidationError(Exception):
    """Raised when the input URL is malformed or missing."""

    def __init__(self, message="Invalid URL. Please provide a full URL starting with http:// or https://"):
        self.message = message
        self.status_code = 400
        super().__init__(self.message)


class AuditTimeoutError(Exception):
    """Raised when the target site takes too long to respond."""

    def __init__(self, url="", timeout_sec=8):
        self.message = f"The site took too long to respond (>{timeout_sec}s). Try again or check the URL."
        self.status_code = 504
        self.url = url
        super().__init__(self.message)


class NotHtmlError(Exception):
    """Raised when the target URL returns a non-HTML content type."""

    def __init__(self, content_type="unknown"):
        self.message = (
            f'The URL returned "{content_type}", not an HTML page. '
            f"Only HTML pages can be audited."
        )
        self.status_code = 422
        self.content_type = content_type
        super().__init__(self.message)


class FetchError(Exception):
    """Raised for network-level failures (DNS, connection refused, etc.)."""

    def __init__(self, message="Could not reach the site. Check the URL and try again."):
        self.message = message
        self.status_code = 502
        super().__init__(self.message)
