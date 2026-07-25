"""
Flask application routes.

Single endpoint: POST /audit
Takes a URL, validates it, fetches the page, parses the HTML, logs to DB,
and returns a structured JSON report.
"""

import traceback
import csv
from io import StringIO
from flask import Blueprint, request, jsonify, Response

from app.validator import validate_url
from app.fetcher import fetch_page
from app.parser import parse_html
from app.database import log_audit, get_previous_audit, get_recent_audits
from app.errors import ValidationError, AuditTimeoutError, NotHtmlError, FetchError

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/audit", methods=["POST"])
def audit():
    """
    Audit a URL and return a structured report.

    Request body (JSON):
        {"url": "https://example.com"}

    Success response (200):
        {
            "success": true,
            "data": {
                "url": "https://example.com",
                "status_code": 200,
                "response_time_ms": 342,
                "title": "Example Domain",
                "meta_description": "...",
                "h1_count": 1,
                "total_images": 3,
                "images_missing_alt": 1,
                "word_count": 256
            }
        }

    Error response (4xx/5xx):
        {
            "success": false,
            "error": "Human-readable error message"
        }
    """
    try:
        # Parse request body
        body = request.get_json(silent=True) or {}
        raw_url = body.get("url", "")

        # Step 1: Validate the URL
        url = validate_url(raw_url)

        # Step 2: Fetch the page
        fetch_result = fetch_page(url)

        # Step 3: Parse the HTML
        parsed = parse_html(fetch_result["html"])

        # Build the response
        result = {
            "url": url,
            "status_code": fetch_result["status_code"],
            "response_time_ms": fetch_result["response_time_ms"],
            **parsed,
        }

        # Step 4: Fetch previous audit for historical comparison
        try:
            previous = get_previous_audit(url)
            if previous:
                result["previous_audit"] = previous
        except Exception:
            traceback.print_exc()

        # Step 5: Log to database (fire-and-forget)
        try:
            log_audit(url, result=result)
        except Exception:
            # Log DB errors but don't fail the audit
            traceback.print_exc()

        return jsonify({"success": True, "data": result}), 200

    except (ValidationError, AuditTimeoutError, NotHtmlError, FetchError) as e:
        # Known, expected errors — return the user-friendly message
        # Log failed audits too
        try:
            log_audit(raw_url if "raw_url" in dir() else "unknown", error_message=e.message)
        except Exception:
            pass

        return jsonify({"success": False, "error": e.message}), e.status_code

    except Exception as e:
        # Unknown errors — never expose internals, never crash
        traceback.print_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Something went wrong on our end. Please try again.",
                }
            ),
            500,
        )


@audit_bp.route("/export/csv", methods=["GET"])
def export_csv():
    """
    Export the most recent successful audit for a URL as CSV.
    Query param: ?url=...
    """
    url = request.args.get("url")
    if not url:
        return jsonify({"success": False, "error": "URL parameter is required."}), 400

    try:
        # Validate URL to ensure consistency
        url = validate_url(url)
    except ValidationError as e:
        return jsonify({"success": False, "error": e.message}), e.status_code

    audit = get_previous_audit(url)
    if not audit:
        return jsonify({"success": False, "error": "No successful audit found for this URL."}), 404

    # Generate CSV
    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers
    headers = [
        "URL", "Status Code", "Response Time (ms)", "Title", "Meta Description",
        "H1 Count", "Total Images", "Images Missing Alt Text", "Word Count",
        "Open Graph Image", "Audited At"
    ]
    cw.writerow(headers)
    
    # Write data row
    cw.writerow([
        audit.get("url"),
        audit.get("status_code"),
        audit.get("response_ms"),
        audit.get("title"),
        audit.get("meta_description"),
        audit.get("h1_count"),
        audit.get("total_images"),
        audit.get("images_missing_alt"),
        audit.get("word_count"),
        audit.get("og_image"),
        audit.get("audited_at")
    ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_{url.replace("https://", "").replace("http://", "").replace("/", "_")}.csv"'}
    )
