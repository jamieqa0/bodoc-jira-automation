from flask import Blueprint, render_template, redirect, url_for

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings")
def settings():
    # Stub — full implementation in Task 2
    return render_template("settings.html")


@settings_bp.route("/settings", methods=["POST"])
def save_settings():
    # Stub — full implementation in Task 2
    return redirect(url_for("settings.settings"))
