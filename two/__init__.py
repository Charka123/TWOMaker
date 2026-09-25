"""Flask application factory."""

from pathlib import Path

from flask import Flask

from .config import load_basins


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(BASINS_PATH=Path(__file__).parent / "data" / "basins.json")
    if test_config:
        app.config.update(test_config)
    app.extensions["basins"] = load_basins(app.config["BASINS_PATH"])

    from .routes import main

    app.register_blueprint(main)
    return app
