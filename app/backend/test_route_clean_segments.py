"""Regression tests for cleanliness per exact traversed walking link."""
import unittest

import networkx as nx
from shapely.geometry import LineString

from walking_router import link_clean_index, route_to_coordinates


class IdentityTransformer:
    def transform(self, x, y):
        return x, y


class RouteCleanSegmentsTests(unittest.TestCase):
    def test_partial_link_uses_source_link_identity(self):
        source = (101, 102, 0)
        scores = {source: {"cleanIndex": 83.2}}
        self.assertEqual(
            link_clean_index(scores, "__route_start__", 102, 0,
                             {"source_edge": source}), 83.2
        )
        self.assertIsNone(link_clean_index(scores, 101, 999, 0, {}))

    def test_each_traversed_segment_keeps_its_own_score(self):
        graph = nx.MultiDiGraph()
        graph.add_node(1, x=127.0, y=37.5)
        graph.add_node(2, x=127.001, y=37.5)
        graph.add_node(3, x=127.002, y=37.5)
        graph.add_edge(1, 2, key=0, length=100.0,
                       geometry=LineString([(127.0, 37.5), (127.001, 37.5)]))
        graph.add_edge(2, 3, key=0, length=100.0,
                       geometry=LineString([(127.001, 37.5), (127.002, 37.5)]))
        scores = {(1, 2, 0): {"cleanIndex": 92.0}}

        coordinates, distance, segments = route_to_coordinates(
            graph, [1, 2, 3], IdentityTransformer(), scores
        )
        self.assertEqual(distance, 200.0)
        self.assertEqual(len(coordinates), 3)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["cleanIndex"], 92.0)
        self.assertIsNone(segments[1]["cleanIndex"])
        self.assertEqual(segments[0]["coordinates"][-1],
                         segments[1]["coordinates"][0])


if __name__ == "__main__":
    unittest.main()
