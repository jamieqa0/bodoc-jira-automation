import os
from datetime import datetime

from flask import Flask

from blueprints.reports import reports_bp
from blueprints.settings import settings_bp

_START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M")


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    @app.context_processor
    def inject_start_time():
        return {"app_updated": _START_TIME}

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True, use_reloader=False)
