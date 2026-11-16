"""Smoking zone CSV tests; do not invent locations or reuse non-smoking data."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoking_zones import load_smoking_zones


class SmokingZonesTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get("LUNG_SMOKING_ZONES_CSV")

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("LUNG_SMOKING_ZONES_CSV", None)
        else:
            os.environ["LUNG_SMOKING_ZONES_CSV"] = self.previous

    def test_no_csv_does_not_invent_zones(self):
        os.environ.pop("LUNG_SMOKING_ZONES_CSV", None)
        self.assertEqual(load_smoking_zones(), {"source": "not-configured", "zones": []})

    def test_actual_csv_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zones.csv"
            path.write_text("시설명,위도,경도\n테스트 시설,37.50,127.02\n", encoding="utf-8-sig")
            os.environ["LUNG_SMOKING_ZONES_CSV"] = str(path)
            data = load_smoking_zones()
            self.assertEqual(data["source"], "configured-csv")
            self.assertEqual(len(data["zones"]), 1)
            self.assertEqual(data["zones"][0]["name"], "테스트 시설")

    def test_invalid_rows_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "zones.csv"
            os.environ["LUNG_SMOKING_ZONES_CSV"] = str(path)
            path.write_text("시설명,위도,경도\n오류 시설,nan,127.02\n", encoding="utf-8-sig")
            with self.assertRaises(ValueError):
                load_smoking_zones()


if __name__ == "__main__":
    unittest.main()
