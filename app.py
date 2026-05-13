import os
import subprocess

from flask import Flask

from blueprints.reports import reports_bp
from blueprints.settings import settings_bp
from config.ui_settings_loader import load_ui_settings


def _last_commit_date() -> str:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d"],
            capture_output=True, text=True, timeout=3,
        )
        date = result.stdout.strip()
        if date:
            return date
    except Exception:
        pass
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


_LAST_UPDATED = _last_commit_date()


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    @app.context_processor
    def inject_globals():
        ui = load_ui_settings()
        return {
            "app_updated": _LAST_UPDATED,
            "atlassian_user": ui.get("atlassian_user", ""),
        }

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True, use_reloader=False)
