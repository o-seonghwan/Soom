"""Dependency-free checks for the optional model CSV adapter."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from model_risk_adapter import load_model_risks
from risk_provider import get_risk_snapshot


class ModelRiskAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "1_위험지도_지점.csv"

    def write_csv(self, body):
        self.path.write_text(body, encoding="utf-8-sig")

    def test_imports_model_scores_without_inverting_or_rescaling(self):
        self.write_csv("노드 ID,위도,경도,위험점수,위험확률\n"
                       "100,37.501,127.029,90.2,0.31\n"
                       "101,37.502,127.030,12.5,0.08\n")
        locations = load_model_risks(self.path)
        self.assertEqual([x["score"] for x in locations], [90.2, 12.5])
        self.assertEqual([x["id"] for x in locations], ["model-node-100", "model-node-101"])
        self.assertEqual(locations[0]["radiusM"], 21.0)

    def test_missing_columns_fail(self):
        self.write_csv("노드 ID,위도,경도\n100,37.5,127.0\n")
        with self.assertRaisesRegex(ValueError, "필수 컬럼"):
            load_model_risks(self.path)

    def test_invalid_rows_fail(self):
        for row in ("100,nan,127.0,50", "100,37.5,127.0,101", "100,37.5,127.0,-1"):
            with self.subTest(row=row):
                self.write_csv("노드 ID,위도,경도,위험점수\n" + row + "\n")
                with self.assertRaises(ValueError):
                    load_model_risks(self.path)

    def test_duplicate_nodes_fail(self):
        self.write_csv("노드 ID,위도,경도,위험점수\n"
                       "100,37.5,127.0,50\n100,37.6,127.1,70\n")
        with self.assertRaisesRegex(ValueError, "중복"):
            load_model_risks(self.path)

    def test_empty_csv_fail(self):
        self.write_csv("노드 ID,위도,경도,위험점수\n")
        with self.assertRaisesRegex(ValueError, "비어"):
            load_model_risks(self.path)

    def test_mock_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            result = get_risk_snapshot()
        self.assertEqual(result["source"], "mock")
        self.assertEqual(len(result["locations"]), 3)

    def test_model_when_env_provided(self):
        self.write_csv("노드 ID,위도,경도,위험점수\n100,37.5,127.0,80\n")
        with patch.dict(os.environ, {"LUNG_RISK_CSV": str(self.path)}):
            result = get_risk_snapshot()
        self.assertEqual(result["source"], "model-csv")
        self.assertEqual(result["locations"][0]["score"], 80)

    def test_missing_explicit_model_file_must_not_use_mock(self):
        with patch.dict(os.environ, {"LUNG_RISK_CSV": str(self.path)}):
            with self.assertRaises(FileNotFoundError):
                get_risk_snapshot()


if __name__ == "__main__":
    unittest.main()
