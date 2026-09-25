from io import BytesIO
import unittest

from PIL import Image

from two import create_app
from two.models import Basin, Disturbance, Outlook
from two.rendering import (HEIGHT, WIDTH, coordinate_label, grid_ticks,
                           probability_color, project, render_outlook)


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.basin = Basin("north-atlantic", "North Atlantic", 0, 60, -100, 0)
        self.item = dict(name="Test", description="Test disturbance", latitude=15,
                         longitude=-45, probability_48h=20, probability_7d=80,
                         marking_type="x_in_area",
                         area=dict(south=10, north=20, west=-50, east=-40))

    def image(self, item=None, period="7d"):
        outlook = Outlook(self.basin, [Disturbance.from_dict(item or self.item)])
        return Image.open(BytesIO(render_outlook(outlook, period)))

    def pixel(self, image, lat, lon):
        return image.getpixel(tuple(int(value) for value in project(self.basin, lat, lon)))

    def test_color_thresholds(self):
        for probability, color in [(0, "#FFFF00"), (39, "#FFFF00"),
                                   (40, "#FF6A00"), (60, "#FF6A00"),
                                   (61, "#FF0202"), (100, "#FF0202")]:
            self.assertEqual(probability_color(probability), color)

    def test_coordinate_labels_and_grid_bounds(self):
        self.assertEqual(coordinate_label(-80), "80°W")
        self.assertEqual(coordinate_label(20), "20°E")
        self.assertEqual(coordinate_label(-10, latitude=True), "10°S")
        self.assertEqual(coordinate_label(60, latitude=True), "60°N")
        self.assertEqual(coordinate_label(0), "0°")
        self.assertEqual(list(grid_ticks(-97, -62)), [-90, -80, -70])

    def test_grid_is_rendered_over_ocean(self):
        with Image.open(BytesIO(render_outlook(Outlook(self.basin)))) as image:
            x, y = (int(value) for value in project(self.basin, 30, -30))
            colors = {image.getpixel((px, py))
                      for px in range(x - 2, x + 14) for py in range(y - 2, y + 14)}
            self.assertIn((25, 59, 85), colors)
            self.assertGreater(len(colors), 1)

    def test_great_lakes_are_water_and_nearby_land_is_preserved(self):
        png = render_outlook(Outlook(self.basin))
        with Image.open(BytesIO(png)) as image:
            for name, lat, lon in [
                ("Superior", 47.5, -87.5), ("Michigan", 43.5, -87),
                ("Huron", 44.5, -82.5), ("Erie", 42, -81),
                ("Ontario", 43.7, -77.8),
            ]:
                with self.subTest(lake=name):
                    self.assertEqual(self.pixel(image, lat, lon), (25, 59, 85))
            self.assertEqual(self.pixel(image, 43.5, -85), (139, 155, 145))

    def test_png_and_selected_period(self):
        for period, color in [("7d", (255, 2, 2)), ("48h", (255, 255, 0))]:
            with self.image(period=period) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (WIDTH, HEIGHT))
                self.assertEqual(self.pixel(image, 15, -45), color)

    def test_area_only_has_outline_but_no_x(self):
        item = self.item | {"marking_type": "area_only", "latitude": None, "longitude": None}
        with self.image(item) as image:
            self.assertEqual(self.pixel(image, 20, -45), (255, 2, 2))
            self.assertNotEqual(self.pixel(image, 15, -45), (255, 2, 2))

    def test_ellipse_has_curved_outline_and_supports_each_marking(self):
        for marking in ["area_only", "x_in_area", "x_to_area"]:
            item = self.item | {"marking_type": marking,
                               "area": self.item["area"] | {"shape": "ellipse"}}
            if marking == "area_only":
                item.update(latitude=None, longitude=None)
            elif marking == "x_to_area":
                item["longitude"] = -60
            with self.subTest(marking=marking), self.image(item) as image:
                self.assertEqual(self.pixel(image, 20, -45), (255, 2, 2))
                self.assertNotEqual(self.pixel(image, 20, -50), (255, 2, 2))
                if marking != "area_only":
                    self.assertEqual(self.pixel(image, item["latitude"], item["longitude"]), (255, 2, 2))

    def test_arrow_connects_external_x_to_area(self):
        item = self.item | {"marking_type": "x_to_area", "longitude": -60}
        with self.image(item) as image:
            self.assertEqual(self.pixel(image, 15, -60), (255, 2, 2))
            self.assertEqual(self.pixel(image, 15, -55), (255, 2, 2))

    def test_image_endpoint(self):
        client = create_app({"TESTING": True}).test_client()
        response = client.post("/api/outlook/image", json={
            "basin_id": self.basin.id, "disturbances": [self.item]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertIn("north-atlantic-7d-outlook.png", response.headers["Content-Disposition"])
        with Image.open(BytesIO(response.data)) as image:
            image.verify()

    def test_image_endpoint_validation_and_empty_basin(self):
        client = create_app({"TESTING": True}).test_client()
        payload = {"basin_id": self.basin.id, "disturbances": []}
        self.assertEqual(client.post("/api/outlook/image", json=payload).status_code, 200)
        for invalid in [None, [], payload | {"period": "bad"}, payload | {"period": []},
                        payload | {"basin_id": "invalid"},
                        payload | {"disturbances": [self.item | {"probability_7d": 101}]}]:
            with self.subTest(invalid=invalid):
                self.assertEqual(client.post("/api/outlook/image", json=invalid).status_code, 400)


if __name__ == "__main__":
    unittest.main()
