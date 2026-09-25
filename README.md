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

Choose one of three disturbance marking types:

- **Area of interest (no X)**: formation area only; no current X position or arrow.
- **X moving into an area (arrow)**: current X position outside the formation area;
  an arrow is defined from that position toward the area's center.
- **X within an area**: current X position inside the formation area; no arrow.

Every type includes a name, description, both probabilities, and a formation
area specified by south/north latitude and west/east longitude bounds. These
rectangles are a simple initial data representation, not rendered map shapes.
Both the area and any X position must be within the basin. Area boundaries count
as inside.

## Basin images

After adding disturbances, select the 7-day (default) or 48-hour probability
horizon and click **Generate image**. The preview and **Download PNG** link show
a 1200×720 basin image with coastlines, country borders, U.S. state boundaries,
and disturbance markings. An empty
outlook generates a plain basin map. Adding/removing disturbances or changing
the horizon clears the previous preview so it cannot be mistaken for current data.

Markings use the selected horizon: below 40% is `#FFFF00`, 40–60% inclusive is
`#FF6A00`, and above 60% is `#FF0202`. Areas are rectangular outlines; X markers
and arrows use the same color. Arrow endpoints follow the existing model.

The renderer uses Pillow and bundled public-domain Natural Earth 1:50m land,
lake, country border, and U.S. state boundary layers;
no network connection, map service, or API key is required at runtime. The simple
equirectangular basemap uses the configured basin bounds. Coastlines are simplified
and very small islands may be omitted. See `two/data/README.md` for source details.
PNG files contain no title, legend, or forecast text and are unofficial products.
Latitude and longitude grid lines are spaced every 10 degrees, with hemisphere
labels along the left and bottom edges in bundled Source Sans 3 Regular. The
grid sits beneath disturbance markings. Font licensing is in `two/data/fonts/`.

Use the Flask URL above rather than opening `two/templates/index.html` directly
or serving it with a static preview/Live Server. Flask renders the template and
provides the API. If the basin selector displays literal `{{ basin.name }}`, you
are viewing the unrendered template. The selector currently has one option:
North Atlantic.

## Structure

- `two/models.py`: framework-independent Basin, Outlook, Disturbance, and FormationArea dataclasses.
- `two/data/basins.json`: configurable basin names and rectangular geographic bounds.
- `two/config.py`: loads and validates basin configuration.
- `two/routes.py`: single page and stateless `POST /api/outlook` validation endpoint.
- `two/rendering.py`: basin and disturbance PNG rendering, independent of Flask.
- `two/templates/` and `two/static/`: HTML, CSS, and plain JavaScript interface.

The API accepts `basin_id` and a `disturbances` array with `name`, `latitude`,
`longitude`, `description`, `probability_48h`, `probability_7d`, `marking_type`, and
`area`. The required `marking_type` is `area_only`, `x_to_area`, or `x_in_area`.
`area` contains numeric `south`, `north`, `west`, and `east` bounds. For `area_only`,
omit latitude/longitude or set both to null; other types require both coordinates.
`Disturbance.from_dict()` reconstructs nested area data; the `arrow` property
derives endpoints for future renderers without duplicating stored coordinates.
Older payloads without marking type and area must be updated. The API returns the
validated outlook as JSON, or a JSON error with HTTP 400. Validation runs on the
server as well as in the form. Alternate JSON configuration paths may be supplied
through the application factory's `BASINS_PATH` config key. Current rectangular
bounds do not support crossing the antimeridian.

`POST /api/outlook/image` accepts the same outlook payload plus optional `period`
(`7d` or `48h`) and returns a PNG attachment, or a JSON error with HTTP 400.

There is no database, persistence, interactive map, or text product generation
yet. This tool does not produce official NHC or
government forecasts.

## Tests

```sh
python -m unittest discover -s tests -v
```
