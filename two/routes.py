"""HTTP input handling; outlooks are submitted explicitly, not stored globally."""

from dataclasses import asdict
from io import BytesIO

from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from .models import Disturbance, Outlook, MARKING_TYPES
from .rendering import render_outlook

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index.html", basins=current_app.extensions["basins"].values(),
                           marking_types=MARKING_TYPES)


@main.get("/api/basins/<basin_id>/image")
def basin_image(basin_id):
    basin = current_app.extensions["basins"].get(basin_id)
    if basin is None:
        return jsonify(error="Unknown basin."), 404
    return send_file(BytesIO(render_outlook(Outlook(basin))), mimetype="image/png", max_age=3600)


def parse_outlook(payload):
    if not isinstance(payload, dict):
        raise ValueError("Submit an outlook as a JSON object.")
    try:
        basin_id = payload.get("basin_id")
        if not isinstance(basin_id, str) or basin_id not in current_app.extensions["basins"]:
            raise ValueError("Select a configured basin.")
        items = payload.get("disturbances")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError("Disturbances must be a list of objects.")
        return Outlook(
            basin=current_app.extensions["basins"][basin_id],
            disturbances=[Disturbance.from_dict(item) for item in items],
        )
    except (TypeError, AttributeError):
        raise ValueError("Each disturbance must include valid fields and formation area bounds.") from None


@main.post("/api/outlook")
def validate_outlook():
    try:
        outlook = parse_outlook(request.get_json(silent=True))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(asdict(outlook))


@main.post("/api/outlook/image")
def outlook_image():
    payload = request.get_json(silent=True)
    try:
        outlook = parse_outlook(payload)
        period = payload.get("period", "7d")
        png = render_outlook(outlook, period)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return send_file(BytesIO(png), mimetype="image/png", as_attachment=True,
                     download_name=f"{outlook.basin.id}-{period}-outlook.png", max_age=0)
