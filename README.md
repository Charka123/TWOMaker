# Tropical Weather Outlook Generator

A minimal Flask application for assembling custom, unofficial tropical weather
outlooks. North Atlantic is the only configured basin initially.

## Run locally

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
flask --app two run --debug
```

Open http://127.0.0.1:5000. Add disturbances with a name, coordinates, description,
and whole-number 48-hour and 7-day formation probabilities (0–100%). Negative
longitudes indicate west. Entries must fall inside the configured basin bounds.
You can remove entries; page data is held in memory and is lost on reload.

## Structure

- `two/models.py`: framework-independent Basin, Outlook, and Disturbance dataclasses.
- `two/data/basins.json`: configurable basin names and rectangular geographic bounds.
- `two/config.py`: loads and validates basin configuration.
- `two/routes.py`: single page and stateless `POST /api/outlook` validation endpoint.
- `two/templates/` and `two/static/`: HTML, CSS, and plain JavaScript interface.

The API accepts `basin_id` and a `disturbances` array with `name`, `latitude`,
`longitude`, `description`, `probability_48h`, and `probability_7d`. It returns the
validated outlook as JSON, or a JSON error with HTTP 400. Validation runs on the
server as well as in the form. Alternate JSON configuration paths may be supplied
through the application factory's `BASINS_PATH` config key. Current rectangular
bounds do not support crossing the antimeridian.

There is no database, persistence, interactive map, text product generation,
image generation, or export yet. This tool does not produce official NHC or
government forecasts.

## Tests

```sh
python -m unittest discover -s tests -v
```
