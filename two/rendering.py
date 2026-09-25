"""Deterministic, offline basin PNGs from validated outlook data."""

from functools import lru_cache
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import validate_number

WIDTH, HEIGHT = 1200, 720
OCEAN = "#193B55"
LAND = "#8B9B91"
COUNTRY_BORDER = "#344A50"
STATE_BORDER = "#596E70"
GRID_INTERVAL = 10


def coordinate_label(value, latitude=False):
    if value == 0:
        return "0°"
    direction = ("N" if value > 0 else "S") if latitude else ("E" if value > 0 else "W")
    return f"{abs(value):g}°{direction}"


def grid_ticks(lower, upper):
    start = math.ceil(lower / GRID_INTERVAL) * GRID_INTERVAL
    return range(start, math.floor(upper / GRID_INTERVAL) * GRID_INTERVAL + 1, GRID_INTERVAL)


def draw_graticule(image, basin):
    """Draw a subtle 10-degree grid and readable Source Sans edge labels."""
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.truetype(str(Path(__file__).parent / "data" / "fonts" /
                                 "SourceSans3-Regular.ttf"), 18)
    latitudes = grid_ticks(basin.south, basin.north)
    longitudes = grid_ticks(basin.west, basin.east)
    for latitude in latitudes:
        _, y = project(basin, latitude, basin.west)
        for x in range(0, WIDTH, 12):
            draw.line((x, y, min(x + 5, WIDTH - 1), y), fill=(225, 236, 241, 65))
    for longitude in longitudes:
        x, _ = project(basin, basin.north, longitude)
        for y in range(0, HEIGHT, 12):
            draw.line((x, y, x, min(y + 5, HEIGHT - 1)), fill=(225, 236, 241, 65))

    def label(text, x, y):
        box = draw.textbbox((0, 0), text, font=font)
        width, height = box[2] - box[0], box[3] - box[1]
        x = max(7, min(x - width / 2, WIDTH - width - 7))
        y = max(7, min(y - height / 2, HEIGHT - height - 7))
        draw.rounded_rectangle((x - 4, y - 3, x + width + 4, y + height + 3),
                               radius=3, fill=(16, 33, 44, 225))
        draw.text((x - box[0], y - box[1]), text, font=font, fill="#EAF1F5")

    for latitude in latitudes:
        _, y = project(basin, latitude, basin.west)
        # Reserve the bottom row for longitude labels at the corner.
        label(coordinate_label(latitude, latitude=True), 28, min(y, HEIGHT - 45))
    for longitude in longitudes:
        x, _ = project(basin, basin.south, longitude)
        label(coordinate_label(longitude), x, HEIGHT - 17)


def probability_color(probability):
    validate_number("Formation probability", probability, 0, 100)
    if probability < 40:
        return "#FFFF00"
    if probability <= 60:
        return "#FF6A00"
    return "#FF0202"


def project(basin, latitude, longitude):
    """Equirectangular projection onto the basin image."""
    return (
        (longitude - basin.west) / (basin.east - basin.west) * (WIDTH - 1),
        (basin.north - latitude) / (basin.north - basin.south) * (HEIGHT - 1),
    )


@lru_cache(maxsize=2)
def map_polygons(layer):
    filenames = {"land": "ne_50m_land.geojson", "lakes": "ne_50m_lakes.geojson"}
    path = Path(__file__).parent / "data" / filenames[layer]
    features = json.loads(path.read_text())["features"]
    polygons = []
    for feature in features:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons.append(geometry["coordinates"])
        elif geometry["type"] == "MultiPolygon":
            polygons.extend(geometry["coordinates"])
    return polygons


@lru_cache(maxsize=2)
def boundary_lines(layer):
    """Load national borders or U.S.-only state borders from bundled GeoJSON."""
    filenames = {
        "countries": "ne_50m_admin_0_boundary_lines_land.geojson",
        "us_states": "ne_50m_admin_1_states_provinces_lines.geojson",
    }
    path = Path(__file__).parent / "data" / filenames[layer]
    lines = []
    for feature in json.loads(path.read_text())["features"]:
        if layer == "us_states" and feature["properties"].get("ADM0_A3") != "USA":
            continue
        geometry = feature["geometry"]
        if geometry["type"] == "LineString":
            lines.append(geometry["coordinates"])
        elif geometry["type"] == "MultiLineString":
            lines.extend(geometry["coordinates"])
    return lines


def render_outlook(outlook, period="7d"):
    """Return PNG bytes. Colors use the chosen horizon for every marking."""
    if period not in ("48h", "7d"):
        raise ValueError("Image period must be 48h or 7d.")
    basin = outlook.basin
    image = Image.new("RGB", (WIDTH, HEIGHT), OCEAN)
    draw = ImageDraw.Draw(image)
    # Lake interior rings represent islands; preserve them as land.
    # Draw borders and disturbances afterwards so those overlays remain visible.
    for layer, exterior, interior in [("land", LAND, OCEAN), ("lakes", OCEAN, LAND)]:
        for polygon in map_polygons(layer):
            for index, ring in enumerate(polygon):
                points = [project(basin, lat, lon) for lon, lat in ring]
                draw.polygon(points, fill=exterior if index == 0 else interior)
                draw.line(points, fill="#C3CEC5", width=1)

    for layer, color, width in [("us_states", STATE_BORDER, 1),
                                 ("countries", COUNTRY_BORDER, 2)]:
        for line in boundary_lines(layer):
            draw.line([project(basin, lat, lon) for lon, lat in line],
                      fill=color, width=width)

    draw_graticule(image, basin)
    draw = ImageDraw.Draw(image)

    for disturbance in outlook.disturbances:
        color = probability_color(getattr(disturbance, f"probability_{period}"))
        area = disturbance.area
        left, top = project(basin, area.north, area.west)
        right, bottom = project(basin, area.south, area.east)
        # Opaque outlines preserve the exact requested risk colors.
        if area.shape == "polygon":
            points = [project(basin, *point) for point in area.points]
            for stroke, width in [("#10212C", 7), (color, 3)]:
                draw.line(points + points[:1], fill=stroke, width=width, joint="curve")
        else:
            outline = draw.ellipse if area.shape == "ellipse" else draw.rectangle
            outline((left, top, right, bottom), outline="#10212C", width=7)
            outline((left, top, right, bottom), outline=color, width=3)
        if disturbance.arrow:
            start, end = disturbance.arrow
            x1, y1 = project(basin, *start)
            x2, y2 = project(basin, *end)
            length = math.hypot(x2 - x1, y2 - y1)
            ux, uy = (x2 - x1) / length, (y2 - y1) / length
            head = min(18, length * .4)
            tail = min(14, length * .2)
            shaft_start = (x1 + ux * tail, y1 + uy * tail)
            draw.line((shaft_start, (x2, y2)), fill="#10212C", width=7)
            draw.line((shaft_start, (x2, y2)), fill=color, width=3)
            draw.polygon([
                (x2, y2),
                (x2 - ux * head - uy * head / 2, y2 - uy * head + ux * head / 2),
                (x2 - ux * head + uy * head / 2, y2 - uy * head - ux * head / 2),
            ], fill=color)
        if disturbance.latitude is not None:
            x, y = project(basin, disturbance.latitude, disturbance.longitude)
            for width, stroke in [(9, "#10212C"), (5, color)]:
                draw.line((x - 10, y - 10, x + 10, y + 10), fill=stroke, width=width)
                draw.line((x - 10, y + 10, x + 10, y - 10), fill=stroke, width=width)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
