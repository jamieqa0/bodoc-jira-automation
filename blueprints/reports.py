from flask import Blueprint, render_template, jsonify, Response

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
def index():
    return render_template("index.html")


@reports_bp.route("/run", methods=["POST"])
def run_report():
    # Stub — full implementation in Task 4
    return jsonify({"job_id": "stub"})


@reports_bp.route("/stream/<job_id>")
def stream(job_id):
    # Stub — full implementation in Task 4
    return Response("data: [DONE]\n\n", mimetype="text/event-stream")
