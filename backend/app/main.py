# app/main.py
import os
import sys
from flask import Flask


def create_app():
    app = Flask(__name__)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required. Set it to your Postgres DSN, e.g. postgres://user:pass@host:5432/db"
        )

    app.config["DATABASE_URL"] = database_url

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from api.recalls import recalls_bp

    app.register_blueprint(recalls_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
