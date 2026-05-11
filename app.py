import os

from flask import Flask

from blueprints.reports import reports_bp
from blueprints.settings import settings_bp


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True, use_reloader=False)
