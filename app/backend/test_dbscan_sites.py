"""DBSCAN CSV adapter tests using temporary, real-shaped analysis outputs."""
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dbscan_sites import load_dbscan_sites


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class DbscanSitesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.config = patch.dict(os.environ, {"LUNG_DBSCAN_RESULTS_DIR": str(self.folder)})
        self.config.start()
        self.addCleanup(self.config.stop)
        write_csv(self.folder / "4_입지후보_군집.csv",
                  ["군집", "위도", "경도", "적발건수", "대표장소", "판정", "연도 반복", "장소수"], [{
                      "군집": "0", "위도": "37.498", "경도": "127.028",
                      "적발건수": "45", "대표장소": "테스트 집중지",
                      "판정": "후보 검토", "연도 반복": "예", "장소수": "2",
                  }])
        write_csv(self.folder / "4_입지후보_후보지.csv",
                  ["군집", "순위", "위도", "경도", "접근거리m(보행)", "권장 형태",
                   "노드 ID", "위험확률 OOF", "보행흐름 백분위", "현장 확인"], [{
                      "군집": "0", "순위": "1", "위도": "37.4981",
                      "경도": "127.0281", "접근거리m(보행)": "102.5",
                      "권장 형태": "밀폐형(흐름 상위 25%)",
                      "노드 ID": "n-01", "위험확률 OOF": "0.67",
                      "보행흐름 백분위": "76.0",
                      "현장 확인": "보도 폭 확인",
                  }])

    def test_load_existing_candidate_and_cluster(self):
        data = load_dbscan_sites()
        self.assertEqual(data["source"], "dbscan-analysis-csv")
        self.assertEqual(data["summary"]["clusterCount"], 1)
        self.assertEqual(data["summary"]["candidateCount"], 1)
        self.assertEqual(data["summary"]["reviewClusterCount"], 1)
        self.assertEqual(data["candidates"][0]["walkingDistanceM"], 102.5)
        self.assertEqual(data["parameters"]["epsM"], 30)

    def test_no_placeholder_when_files_missing(self):
        (self.folder / "4_입지후보_후보지.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            load_dbscan_sites()

    def test_invalid_candidate_coordinates_are_rejected(self):
        p = self.folder / "4_입지후보_후보지.csv"
        write_csv(p,
                  ["군집", "순위", "위도", "경도", "접근거리m(보행)", "권장 형태"], [{
                      "군집": "0", "순위": "1", "위도": "0",
                      "경도": "0", "접근거리m(보행)": "100", "권장 형태": "개방형 + 버퍼",
                  }])
        with self.assertRaises(ValueError):
            load_dbscan_sites()


if __name__ == "__main__":
    unittest.main()
