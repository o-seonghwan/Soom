"""Regression checks for real-graph simulation cost and modeled cleanliness bins."""
import sys
import unittest
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_avoidance import edge_metric, weight_function, cleanliness_distribution


class SimulationTests(unittest.TestCase):
    def graph_and_risk(self):
        g = nx.MultiDiGraph()
        g.add_edge("A", "B", key=0, length=100)
        g.add_edge("B", "D", key=0, length=100)
        g.add_edge("A", "C", key=0, length=120)
        g.add_edge("C", "D", key=0, length=120)
        risks = {
            ("A", "B", 0): {"normalizedRisk": .9, "cleanIndex": 10},
            ("B", "D", 0): {"normalizedRisk": .9, "cleanIndex": 10},
            ("A", "C", 0): {"normalizedRisk": .1, "cleanIndex": 90},
            ("C", "D", 0): {"normalizedRisk": .1, "cleanIndex": 90},
        }
        return g, risks

    def test_cost_chooses_shorter_at_zero_and_cleaner_at_high(self):
        g, risks = self.graph_and_risk()
        short = nx.shortest_path(g, "A", "D", weight=weight_function(risks, 0))
        safe = nx.shortest_path(g, "A", "D", weight=weight_function(risks, 6))
        self.assertEqual(short, ["A", "B", "D"])
        self.assertEqual(safe, ["A", "C", "D"])
        dist0, risk0 = edge_metric(g, risks, short, 0)
        dist1, risk1 = edge_metric(g, risks, safe, 6)
        self.assertEqual(dist0, 200)
        self.assertEqual(dist1, 240)
        self.assertLess(risk1, risk0)

    def test_cleanliness_percentiles_respect_length_weights(self):
        g, risks = self.graph_and_risk()
        result = cleanliness_distribution(g, risks)
        self.assertEqual(result["mapped_edge_count"], 4)
        self.assertEqual(result["clean_p20"], 10)
        self.assertEqual(result["clean_p80"], 90)

    def test_unknown_unscored_streets_are_not_counted(self):
        g, risks = self.graph_and_risk()
        g.add_edge("A", "E", key=0, length=20000)
        result = cleanliness_distribution(g, risks)
        self.assertEqual(result["mapped_length_m"], 440)


if __name__ == "__main__":
    unittest.main()
