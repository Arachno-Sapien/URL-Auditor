"""
URL validation using Python's built-in urllib.parse.

No regex — the stdlib URL parser handles the heavy lifting.
We just enforce http/https protocol and basic structural validity.
"""

from urllib.parse import urlparse

from app.errors import ValidationError


def validate_url(raw_input):
    """
    Validate and normalize a URL string.

    Args:
        raw_input: The raw URL input from the user.

    Returns:
        str: The validated, normalized URL.

    Raises:
        ValidationError: If the input is not a valid http/https URL.
    """
    if not raw_input or not isinstance(raw_input, str):
        raise ValidationError("URL is required. Please provide a URL to audit.")

    url = raw_input.strip()

    if not url:
        raise ValidationError("URL is required. Please provide a URL to audit.")

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError(
            "Invalid URL format. Please provide a full URL starting with http:// or https://"
        )

    # Must have a scheme and a network location (domain)
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError(
            "Invalid URL format. Please provide a full URL starting with http:// or https://"
        )

    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            f'Unsupported protocol "{parsed.scheme}://". Only http:// and https:// URLs are supported.'
        )

    return url
