import unittest

from two import create_app
from two.models import Basin, Disturbance, Outlook


VALID = dict(name="Invest 90L", latitude=15.5, longitude=-45.2,
             description="Disorganized showers over the central Atlantic.",
             probability_48h=20, probability_7d=50, marking_type="x_in_area",
             area=dict(south=10, north=20, west=-50, east=-40))


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.basin = Basin("north-atlantic", "North Atlantic", 0, 60, -100, 0)

    def test_outlooks_do_not_share_disturbances(self):
        first, second = Outlook(self.basin), Outlook(self.basin)
        first.add_disturbance(Disturbance.from_dict(VALID))
        self.assertEqual(len(first.disturbances), 1)
        self.assertEqual(second.disturbances, [])

    def test_invalid_disturbance_values(self):
        for field, value in [("latitude", 91), ("longitude", -181),
                             ("latitude", float("nan")), ("longitude", float("inf")),
                             ("probability_48h", -1), ("probability_7d", 101),
                             ("probability_7d", 25.5), ("probability_48h", True),
                             ("name", " "), ("description", " ")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                Disturbance.from_dict(VALID | {field: value})

    def test_probability_endpoints(self):
        Disturbance.from_dict(VALID | {"probability_48h": 0, "probability_7d": 100})

    def test_basin_bounds(self):
        for bounds in [(60, 0, -100, 0), (0, 60, 0, -100),
                       (-91, 60, -100, 0), (0, 60, -181, 0)]:
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                Basin("test", "Test", *bounds)

    def test_three_marking_types_and_arrow(self):
        inside = Disturbance.from_dict(VALID)
        self.assertIsNone(inside.arrow)
        area_only = Disturbance.from_dict(VALID | {
            "marking_type": "area_only", "latitude": None, "longitude": None})
        self.assertIsNone(area_only.arrow)
        moving = Disturbance.from_dict(VALID | {
            "marking_type": "x_to_area", "longitude": -60})
        self.assertEqual(moving.arrow, ((15.5, -60), (15, -45)))
        Outlook(self.basin, [inside, area_only, moving])

    def test_marking_location_rules(self):
        for overrides in [
            {"marking_type": "unknown"}, {"marking_type": []},
            {"marking_type": "area_only"},
            {"marking_type": "x_to_area"},
            {"latitude": None}, {"longitude": -60},
            {"area": None},
            {"area": dict(south=20, north=10, west=-50, east=-40)},
            {"area": dict(south=10, north=20, west=-40, east=-50)},
            {"area": dict(south=10, north=float("nan"), west=-50, east=-40)},
        ]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                Disturbance.from_dict(VALID | overrides)

    def test_area_must_fit_basin_even_without_x(self):
        disturbance = Disturbance.from_dict(VALID | {
            "marking_type": "area_only", "latitude": None, "longitude": None,
            "area": dict(south=-1, north=20, west=-50, east=-40)})
        with self.assertRaises(ValueError):
            Outlook(self.basin, [disturbance])

    def test_x_on_area_boundary_is_inside(self):
        Disturbance.from_dict(VALID | {"latitude": 10, "longitude": -50})
        with self.assertRaises(ValueError):
            Disturbance.from_dict(VALID | {
                "latitude": 10, "longitude": -50, "marking_type": "x_to_area"})

    def test_out_of_basin_rejected_on_creation_and_add(self):
        disturbance = Disturbance.from_dict(VALID | {"latitude": -15,
            "area": dict(south=-20, north=-10, west=-50, east=-40)})
        with self.assertRaises(ValueError):
            Outlook(self.basin, [disturbance])
        outlook = Outlook(self.basin)
        with self.assertRaises(ValueError):
            outlook.add_disturbance(disturbance)
        self.assertEqual(outlook.disturbances, [])


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app({"TESTING": True}).test_client()

    def test_page_and_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"North Atlantic", response.data)
        self.assertIn(b'<option value="north-atlantic">North Atlantic</option>', response.data)
        self.assertNotIn(b"{{", response.data)
        self.assertNotIn(b"{%", response.data)
        self.assertIn(b"unofficial", response.data)
        for path in ["/static/app.js", "/static/style.css"]:
            with self.client.get(path) as asset:
                self.assertEqual(asset.status_code, 200)

    def test_outlook_round_trip(self):
        response = self.client.post("/api/outlook", json={
            "basin_id": "north-atlantic", "disturbances": [VALID]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["disturbances"], [VALID])
        self.assertEqual(response.json["basin"]["id"], "north-atlantic")

    def test_invalid_payloads(self):
        for payload in [[], {}, {"basin_id": []},
                        {"basin_id": "unknown", "disturbances": []},
                        {"basin_id": "north-atlantic", "disturbances": [{}]},
                        {"basin_id": "north-atlantic", "disturbances": [VALID | {"name": None}]},
                        {"basin_id": "north-atlantic", "disturbances": [VALID | {"latitude": -10}]}]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/outlook", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)

    def test_markings_api_round_trip(self):
        for overrides in [
            {"marking_type": "area_only", "latitude": None, "longitude": None},
            {"marking_type": "x_to_area", "longitude": -60},
            {"marking_type": "x_in_area"},
        ]:
            item = VALID | overrides
            with self.subTest(marking=item["marking_type"]):
                response = self.client.post("/api/outlook", json={
                    "basin_id": "north-atlantic", "disturbances": [item]})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["disturbances"], [item])

    def test_malformed_area_payload(self):
        for area in [None, [], {}, {"south": "ten"}, VALID["area"] | {"extra": 1}]:
            with self.subTest(area=area):
                response = self.client.post("/api/outlook", json={
                    "basin_id": "north-atlantic", "disturbances": [VALID | {"area": area}]})
                self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
