from io import BytesIO
import math
import unittest

from PIL import Image

from two import create_app
from two.models import PolygonArea


class PolygonTests(unittest.TestCase):
    def setUp(self):
        self.points = [[10,-60],[20,-60],[20,-55],[15,-55],[15,-50],[10,-50]]
        self.item = dict(name='Drawn area', description='Freehand outline', latitude=None,
                         longitude=None, probability_48h=20, probability_7d=60,
                         marking_type='area_only', area=dict(shape='polygon',points=self.points))
        self.client = create_app({'TESTING':True}).test_client()

    def test_concave_area_and_interior_arrow_target(self):
        area = PolygonArea(self.points)
        self.assertTrue(area.contains(12,-52))
        self.assertTrue(area.contains(15,-55))
        self.assertFalse(area.contains(18,-52))
        self.assertTrue(area.contains(*area.center))
        self.assertEqual((area.south,area.north,area.west,area.east), (10,20,-60,-50))

    def test_invalid_outlines(self):
        for points in [[], [[10,-60],[20,-50]], [[10,-60],[15,-55],[20,-50]],
                       [[10,-60],[20,-50],[10,-50],[20,-60]],
                       [[10,-60],[20,-50],[10,-60],[10,-50]],
                       [[91,-60],[20,-50],[10,-50]], [[10,-60],[20,float('nan')],[10,-50]],
                       [[10,-60]]*501]:
            with self.subTest(points=points), self.assertRaises(ValueError):
                PolygonArea(points)

    def test_sampled_freehand_outline(self):
        points = [[20+5*math.sin(i*math.tau/100), -50+8*math.cos(i*math.tau/100)]
                  for i in range(100)]
        for outline in [points, list(reversed(points)), points + points[:1]]:
            area = PolygonArea(outline)
            self.assertTrue(area.contains(20,-50))
            self.assertFalse(area.contains(25,-42))
            self.assertTrue(area.contains(*area.center))

    def test_round_trip_and_image(self):
        payload = dict(basin_id='north-atlantic', disturbances=[self.item])
        response = self.client.post('/api/outlook', json=payload)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['disturbances'][0]['area'],self.item['area'])
        response = self.client.post('/api/outlook/image',json=payload)
        self.assertEqual(response.status_code,200)
        with Image.open(BytesIO(response.data)) as image:
            image.verify()

    def test_polygon_validation_at_api(self):
        for item in [self.item | {'area':{'shape':'polygon','points':[[0,-101],[10,-90],[0,-80]]}},
                     self.item | {'marking_type':'x_in_area','latitude':18,'longitude':-52}]:
            response = self.client.post('/api/outlook',json=dict(basin_id='north-atlantic',disturbances=[item]))
            self.assertEqual(response.status_code,400)

    def test_offline_basemap(self):
        self.assertEqual(self.client.get('/api/basins/north-atlantic/image').mimetype,'image/png')
        self.assertEqual(self.client.get('/api/basins/missing/image').status_code,404)
