"""Regression tests for risk CSV semantics and provisional 21m bands."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_risk_adapter import load_model_risks
from risk_decay import effective_risk, cleanliness_index, risk_multiplier
from risk_provider import get_risk_snapshot


class DistanceBandsTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual([risk_multiplier(d) for d in (0, 10, 10.01, 15, 15.01, 21, 21.01)],
                         [1, 1, .65, .65, .30, .30, 0])

    def test_risk_and_clean_index(self):
        expected = [(80, 20), (52, 48), (24, 76), (0, 100)]
        for distance, pair in zip((5, 11, 17, 22), expected):
            risk = effective_risk(80, distance)
            self.assertAlmostEqual(risk, pair[0])
            self.assertAlmostEqual(cleanliness_index(risk), pair[1])

    def test_invalid_input(self):
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                risk_multiplier(value)
        with self.assertRaises(ValueError):
            effective_risk(101, 10)


class ModelCsvTests(unittest.TestCase):
    def write_file(self, directory, text):
        path = Path(directory) / "1_위험지도_지점.csv"
        path.write_text(text, encoding="utf-8-sig")
        return path

    def test_csv_parse_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_file(tmp, "노드 ID,위도,경도,위험점수\n"
                                        "N-1,37.498,127.028,80\n"
                                        "N-2,37.499,127.029,40\n")
            data = load_model_risks(path)
            self.assertEqual(data[0]["radiusM"], 21)
            self.assertEqual(data[0]["cleanIndex"], 20)
            self.assertEqual(data[0]["decayProfile"], "model-v1")
            before = os.environ.get("LUNG_RISK_CSV")
            try:
                os.environ["LUNG_RISK_CSV"] = str(path)
                snapshot = get_risk_snapshot()
                self.assertEqual(snapshot["source"], "model-csv")
                self.assertEqual(len(snapshot["locations"]), 2)
            finally:
                if before is None:
                    os.environ.pop("LUNG_RISK_CSV", None)
                else:
                    os.environ["LUNG_RISK_CSV"] = before

    def test_missing_headers_duplicates_and_nan_rejected(self):
        samples = [
            "노드 ID,위도,경도\nN-1,37.5,127.0\n",
            "노드 ID,위도,경도,위험점수\nN-1,37.5,127.0,80\nN-1,37.6,127.0,60\n",
            "노드 ID,위도,경도,위험점수\nN-1,37.5,127.0,nan\n",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for sample in samples:
                with self.assertRaises(ValueError):
                    load_model_risks(self.write_file(tmp, sample))

    def test_missing_config_is_mock_and_bad_config_fails_closed(self):
        before = os.environ.get("LUNG_RISK_CSV")
        try:
            os.environ.pop("LUNG_RISK_CSV", None)
            self.assertEqual(get_risk_snapshot()["source"], "mock")
            os.environ["LUNG_RISK_CSV"] = "/does/not/exist.csv"
            with self.assertRaises(FileNotFoundError):
                get_risk_snapshot()
        finally:
            if before is None:
                os.environ.pop("LUNG_RISK_CSV", None)
            else:
                os.environ["LUNG_RISK_CSV"] = before


if __name__ == "__main__":
    unittest.main()
