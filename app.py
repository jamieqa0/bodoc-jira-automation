from flask import Flask, redirect, url_for

from blueprints.reports import reports_bp
from blueprints.settings import settings_bp


def create_app() -> Flask:
    app = Flask(__name__)

    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    @app.route("/")
    def root():
        return redirect(url_for("reports.index"))

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)
