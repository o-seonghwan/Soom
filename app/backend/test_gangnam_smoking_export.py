"""Regression tests for the Gangnam smoking-area workbook export adapter."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

SCRIPT = Path(__file__).parents[2] / "notebooks" / "02_preprocessing" / "1_강남구_흡연구역_앱연결.py"
spec = importlib.util.spec_from_file_location("gangnam_smoking_export", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GangnamSmokingExportTests(unittest.TestCase):
    def write_workbook(self, folder, name="강남구_흡연구역_전처리.xlsx", verified="검증완료"):
        source = Path(folder) / name
        book = Workbook()
        sheet = book.active
        sheet.append(["주소", "좌표", "비고", "출처", "위치검증"])
        sheet.append(["서울특별시 강남구 테스트로 10", "37.50000000, 127.02000000", "건물 옆", "원본 자료", verified])
        sheet.append(["서울특별시 강남구 테스트로 20", "", "확인 안 됨", "원본 자료", ""])
        book.save(source)
        book.close()
        return source

    def test_verified_only_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.write_workbook(folder)
            out = Path(folder) / "zones.csv"
            result = module.convert(source, out)
            self.assertEqual(result["exported"], 1)
            self.assertIn("locationAccuracy", out.read_text(encoding="utf-8-sig"))
            self.assertIn("verified", out.read_text(encoding="utf-8-sig"))

    def test_unverified_is_rejected_without_explicit_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.write_workbook(folder, verified="")
            with self.assertRaises(ValueError):
                module.convert(source, Path(folder) / "zones.csv")

    def test_address_level_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.write_workbook(folder, verified="")
            out = Path(folder) / "zones.csv"
            self.assertEqual(module.convert(source, out, include_address_level=True)["exported"], 1)
            self.assertIn("address-level", out.read_text(encoding="utf-8-sig"))

    def test_unrelated_dataset_name_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.write_workbook(folder, name="흡연단속내역.xlsx")
            with self.assertRaises(ValueError):
                module.convert(source, Path(folder) / "zones.csv")


if __name__ == "__main__":
    unittest.main()
