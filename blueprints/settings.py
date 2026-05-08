from flask import Blueprint, flash, redirect, render_template, request, url_for

from config.ui_settings_loader import load_ui_settings, save_ui_settings

settings_bp = Blueprint("settings", __name__)

_REQUIRED_FIELDS = ("atlassian_url", "atlassian_api_token", "confluence_space_key")
_ALL_FIELDS = _REQUIRED_FIELDS + ("qa_report_parent_id", "mor_parent_id")


@settings_bp.route("/settings", methods=["GET"])
def settings():
    current = load_ui_settings()
    return render_template("settings.html", settings=current)


@settings_bp.route("/settings", methods=["POST"])
def save_settings():
    existing = load_ui_settings()
    is_first_run = not existing

    data = {field: request.form.get(field, "").strip() for field in _ALL_FIELDS}

    missing = [f for f in _REQUIRED_FIELDS if not data[f]]
    if missing:
        flash("필수 항목을 모두 입력해주세요.", "error")
        return render_template("settings.html", settings=data)

    save_ui_settings(data)
    flash("설정이 저장되었습니다.", "success")

    if is_first_run:
        return redirect(url_for("reports.index"))
    return redirect(url_for("settings.settings"))
