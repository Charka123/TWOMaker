import unittest

from two import create_app
from two.models import Basin, Disturbance, Outlook


VALID = dict(name="Invest 90L", latitude=15.5, longitude=-45.2,
             description="Disorganized showers over the central Atlantic.",
             probability_48h=20, probability_7d=50)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.basin = Basin("north-atlantic", "North Atlantic", 0, 60, -100, 0)

    def test_outlooks_do_not_share_disturbances(self):
        first, second = Outlook(self.basin), Outlook(self.basin)
        first.add_disturbance(Disturbance(**VALID))
        self.assertEqual(len(first.disturbances), 1)
        self.assertEqual(second.disturbances, [])

    def test_invalid_disturbance_values(self):
        for field, value in [("latitude", 91), ("longitude", -181),
                             ("latitude", float("nan")), ("longitude", float("inf")),
                             ("probability_48h", -1), ("probability_7d", 101),
                             ("probability_7d", 25.5), ("probability_48h", True),
                             ("name", " "), ("description", " ")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                Disturbance(**(VALID | {field: value}))

    def test_probability_endpoints(self):
        Disturbance(**(VALID | {"probability_48h": 0, "probability_7d": 100}))

    def test_basin_bounds(self):
        for bounds in [(60, 0, -100, 0), (0, 60, 0, -100),
                       (-91, 60, -100, 0), (0, 60, -181, 0)]:
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                Basin("test", "Test", *bounds)

    def test_out_of_basin_rejected_on_creation_and_add(self):
        disturbance = Disturbance(**(VALID | {"latitude": -15}))
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


if __name__ == "__main__":
    unittest.main()
