"""
HTTP fetcher — fetches a URL and returns the response body + metadata.

Enforces timeout and content-type checks before returning.
Raises typed exceptions that the route handler maps to HTTP responses.
"""

import requests

from app.errors import AuditTimeoutError, NotHtmlError, FetchError

DEFAULT_TIMEOUT_SEC = 8

# User-Agent so sites don't block us as a bare script
USER_AGENT = "Mozilla/5.0 (compatible; URLAuditor/1.0; +https://github.com/url-auditor)"


def fetch_page(url, timeout_sec=DEFAULT_TIMEOUT_SEC):
    """
    Fetch a URL and return its HTML body, status code, and response time.

    Args:
        url (str): Validated URL to fetch.
        timeout_sec (int): Request timeout in seconds.

    Returns:
        dict: {html, status_code, response_time_ms}

    Raises:
        AuditTimeoutError: If the request exceeds the timeout.
        NotHtmlError: If the response content-type is not HTML.
        FetchError: For any network-level failure.
    """
    try:
        response = requests.get(
            url,
            timeout=timeout_sec,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*",
            },
            # Follow redirects (default is True, being explicit)
            allow_redirects=True,
            # Stream so we can check headers before downloading the full body
            stream=True,
        )

        # Check content-type BEFORE reading the body
        content_type = response.headers.get("Content-Type", "")
        if not _is_html_content_type(content_type):
            response.close()
            raise NotHtmlError(content_type or "unknown")

        # Now read the body (cap at 5MB)
        max_bytes = 5 * 1024 * 1024
        html = response.text[:max_bytes]
        response_time_ms = int(response.elapsed.total_seconds() * 1000)

        return {
            "html": html,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
        }

    except (AuditTimeoutError, NotHtmlError):
        # Re-raise our own exceptions
        raise
    except requests.exceptions.Timeout:
        raise AuditTimeoutError(url, timeout_sec)
    except requests.exceptions.ConnectionError as e:
        raise _categorize_connection_error(e)
    except requests.exceptions.TooManyRedirects:
        raise FetchError("Too many redirects. The URL may be misconfigured.")
    except requests.exceptions.RequestException as e:
        raise FetchError(f"Could not reach the site: {str(e)}")
    except Exception as e:
        raise FetchError(f"Unexpected error fetching the URL: {str(e)}")


def _is_html_content_type(content_type):
    """Check if a content-type header indicates HTML."""
    lower = content_type.lower()
    return "text/html" in lower or "application/xhtml+xml" in lower


def _categorize_connection_error(err):
    """Map requests ConnectionError subtypes to user-friendly messages."""
    err_str = str(err).lower()

    if "nodename nor servname" in err_str or "getaddrinfo failed" in err_str or "name or service not known" in err_str:
        return FetchError("Could not resolve the domain. Check the URL and try again.")

    if "connection refused" in err_str:
        return FetchError("Connection refused by the target server. The site may be down.")

    if "connection reset" in err_str or "connection aborted" in err_str:
        return FetchError("Connection was reset by the target server. Try again later.")

    if "ssl" in err_str or "certificate" in err_str:
        return FetchError(
            "SSL/TLS error when connecting to the site. The site may have an invalid certificate."
        )

    return FetchError("Could not reach the site. Check the URL and try again.")
