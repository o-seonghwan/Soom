"""Verify B2G overlays distinguish model-scored and unscored walking edges."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import networkx as nx
from pyproj import CRS, Transformer
from shapely.geometry import LineString
from b2g_cleanliness import edge_cleanliness_geojson


class B2GGeoJsonTests(unittest.TestCase):
    def graph(self):
        graph = nx.MultiDiGraph()
        graph.graph["crs"] = CRS.from_epsg(5179)
        x1, y1 = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True).transform(127.02, 37.50)
        graph.add_node("a", x=x1, y=y1)
        graph.add_node("b", x=x1+30, y=y1)
        graph.add_node("c", x=x1+60, y=y1)
        graph.add_edge("a", "b", key=0, length=30, geometry=LineString([(x1,y1),(x1+30,y1)]))
        graph.add_edge("b", "c", key=0, length=30)
        return graph

    def test_scored_edge_and_unscored_gray_feature(self):
        result = edge_cleanliness_geojson(self.graph(), {
            ("a","b",0): {"score":52.0,"cleanIndex":48.0}
        })
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(len(result["features"]), 2)
        by_id = {item["properties"]["edgeId"]: item for item in result["features"]}
        scored = by_id["a:b:0"]
        unscored = by_id["b:c:0"]
        self.assertEqual(scored["properties"]["cleanIndex"], 48.0)
        self.assertEqual(scored["properties"]["score"], 52.0)
        self.assertIsNone(unscored["properties"]["cleanIndex"])
        self.assertIsNone(unscored["properties"]["score"])
        self.assertEqual(unscored["geometry"]["type"], "LineString")
        self.assertAlmostEqual(scored["geometry"]["coordinates"][0][0], 127.02, places=4)

    def test_unmatched_edge_rejected(self):
        with self.assertRaises(ValueError):
            edge_cleanliness_geojson(self.graph(), {("missing","b",0): {"score":90,"cleanIndex":10}})


if __name__ == "__main__":
    unittest.main()
