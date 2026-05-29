# app/main.py
import os
import sys
import traceback
from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Set it to your Postgres DSN, e.g. postgres://user:pass@host:5432/db"
        )

    app.config["DATABASE_URL"] = database_url
    allowed_origins = {
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,https://inkyuuu.github.io",
        ).split(",")
        if origin.strip()
    }

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.route("/", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"})

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.error("Unhandled exception:\n%s", traceback.format_exc())
        payload = {"error": "Internal server error"}
        if os.environ.get("DEBUG_API_ERRORS") == "true":
            payload["detail"] = str(error)
        return jsonify(payload), 500

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from api.recalls import recalls_bp

    app.register_blueprint(recalls_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
