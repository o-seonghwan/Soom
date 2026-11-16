"""Regression tests for three-day population EDA feature loading."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import 공통 as C


class PopulationEDALoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.header = "일자,시간,250M격자,행정동코드,생활인구합계\n"

    def write(self, day, value="12", folder=None):
        folder = folder or ("local_resd_250m" if day == "20261027" else f"local_resd_250m_{day}")
        output = self.root / folder
        output.mkdir(parents=True, exist_ok=True)
        filename = output / "features.csv"
        filename.write_text(
            self.header + f"{day[:4]}-{day[4:6]}-{day[6:]},15,다사52255325,11680101 ,{value}\n",
            encoding="utf-8-sig",
        )
        return filename

    def test_three_days_and_suppressed_values(self):
        self.write("20261027", "17")
        self.write("20261028", "*")
        self.write("20261029", "35")
        with patch.object(C, "EDA_ROOT", self.root):
            df = C.load_livepop()
        self.assertEqual(len(df), 3)
        self.assertEqual(df["일자"].tolist(), ["20261027", "20261028", "20261029"])
        self.assertEqual(df["행정동코드"].tolist(), ["11680101"] * 3)
        self.assertEqual(df["생활인구합계"].notna().sum(), 2)
        self.assertEqual(df["생활인구합계"].dropna().tolist(), [17.0, 35.0])

    def test_missing_day_is_not_silently_ignored(self):
        self.write("20261027")
        self.write("20261028")
        with patch.object(C, "EDA_ROOT", self.root):
            with self.assertRaisesRegex(FileNotFoundError, "20261029"):
                C.load_livepop()

    def test_duplicate_day_file_is_rejected(self):
        for day in ("20261027", "20261028", "20261029"):
            self.write(day)
        self.write("20261029", folder="250_LOCAL_RESD_20261029")
        with patch.object(C, "EDA_ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "여러 곳"):
                C.load_livepop()

    def test_duplicate_grid_key_is_rejected(self):
        for day in ("20261027", "20261028", "20261029"):
            self.write(day)
        file = self.root / "local_resd_250m_20261029" / "features.csv"
        file.write_text(file.read_text(encoding="utf-8-sig") +
                        "2026-10-29,15,다사52255325,11680101,22\n", encoding="utf-8-sig")
        with patch.object(C, "EDA_ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "복합키 중복"):
                C.load_livepop()


if __name__ == "__main__":
    unittest.main()
