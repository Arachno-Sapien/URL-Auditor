"""
Flask application factory.

Creates the app, registers blueprints, sets up static file serving,
and adds global error handlers so nothing ever returns a raw stack trace.
"""

import os
from flask import Flask, send_from_directory

from app.routes import audit_bp
from app.database import init_db


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
    )

    # Register the audit blueprint
    app.register_blueprint(audit_bp)

    # Serve the frontend
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # Global error handlers — never leak stack traces to the client
    @app.errorhandler(404)
    def not_found(e):
        return {"success": False, "error": "Endpoint not found."}, 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {"success": False, "error": "Method not allowed. Use POST for /audit."}, 405

    @app.errorhandler(500)
    def internal_error(e):
        return {"success": False, "error": "Something went wrong on our end. Please try again."}, 500

    # Initialize the database on startup
    with app.app_context():
        init_db()

    return app
