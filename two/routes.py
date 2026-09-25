"""HTTP input handling; outlooks are submitted explicitly, not stored globally."""

from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, render_template, request

from .models import Disturbance, Outlook

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index.html", basins=current_app.extensions["basins"].values())


@main.post("/api/outlook")
def validate_outlook():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Submit an outlook as a JSON object."), 400
    try:
        basin_id = payload.get("basin_id")
        if not isinstance(basin_id, str) or basin_id not in current_app.extensions["basins"]:
            raise ValueError("Select a configured basin.")
        items = payload.get("disturbances")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise ValueError("Disturbances must be a list of objects.")
        outlook = Outlook(
            basin=current_app.extensions["basins"][basin_id],
            disturbances=[Disturbance(**item) for item in items],
        )
    except ValueError as error:
        return jsonify(error=str(error)), 400
    except (TypeError, AttributeError):
        return jsonify(error="Each disturbance must include valid values for all seven fields."), 400
    return jsonify(asdict(outlook))
