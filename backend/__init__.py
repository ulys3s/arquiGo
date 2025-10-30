"""Flask application factory for the ConstruyeSeguro platform."""
from pathlib import Path
from flask import Flask, send_from_directory

from . import database
from .routes import api_bp


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).resolve().parent.parent / "frontend"),
        static_url_path="",
    )
    app.config.from_mapping(
        PROJECT_STORAGE=Path(__file__).resolve().parent / "generated",
    )

    if test_config is not None:
        app.config.update(test_config)

    database.init_db()
    database.seed_data()

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def serve_frontend() -> str:
        """Serve the compiled frontend entry point."""
        return send_from_directory(app.static_folder, "index.html")

    return app
