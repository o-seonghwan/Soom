"""Convert the Gangnam smoking-area preprocessing workbook to the app's CSV contract.

Only `강남구_흡연구역.xlsx` or its `_전처리.xlsx` derivative is supported.
This does not accept smoking enforcement, cigarette butt, or no-smoking datasets.

The preprocessing script geocodes *addresses*, not the exact booth entrance.
By default, export only rows explicitly marked as location-verified.
Use --include-address-level to opt in to approximate markers, always labelled
as address-based and not physically verified. Missing/invalid coordinates
are rejected (never geocoded or fabricated here).
"""
import argparse
import csv
import math
import re
from pathlib import Path

from openpyxl import load_workbook


COLUMNS = ("주소", "좌표", "비고", "출처")
VERIFIED_VALUES = {"verified", "현장확인", "현장 검증", "검증완료", "위치확인"}


def normalize(value):
    return str(value or "").strip()


def parse_coordinate(raw):
    parts = re.split(r"\s*[,，]\s*", normalize(raw))
    if len(parts) != 2:
        return None
    try:
        lat, lng = map(float, parts)
    except (ValueError, TypeError):
        return None
    if not all(map(math.isfinite, (lat, lng))):
        return None
    # Same broad Gangnam bounds used by the upstream geocoding script.
    if not (37.44 <= lat <= 37.54 and 127.00 <= lng <= 127.15):
        return None
    return lat, lng


def convert(input_path: Path, output_path: Path, include_address_level=False):
    if input_path.suffix.lower() != ".xlsx":
        raise ValueError("강남구 흡연구역 .xlsx 파일만 입력할 수 있습니다.")
    if not (input_path.stem == "강남구_흡연구역" or input_path.stem == "강남구_흡연구역_전처리"):
        raise ValueError("강남구_흡연구역 원본/전처리 엑셀만 연결할 수 있습니다.")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("원본 파일을 덮어쓸 수 없습니다.")
    book = load_workbook(input_path, read_only=True, data_only=True)
    try:
        sheet = book.active
        rows = sheet.iter_rows(values_only=True)
        columns = {normalize(cell): index for index, cell in enumerate(next(rows))}
        missing = set(COLUMNS) - set(columns)
        if missing:
            raise ValueError("필수 열 누락: " + ", ".join(sorted(missing)))
        verified_col = next((columns[key] for key in ("위치검증", "좌표검증", "위치검증상태") if key in columns), None)
        result = []
        stats = {"total": 0, "missing_or_invalid_coordinate": 0, "not_verified": 0}
        for row in rows:
            stats["total"] += 1
            address = normalize(row[columns["주소"]])
            coord = parse_coordinate(row[columns["좌표"]])
            if not address or not coord:
                stats["missing_or_invalid_coordinate"] += 1
                continue
            verified = verified_col is not None and normalize(row[verified_col]).casefold() in VERIFIED_VALUES
            if not verified and not include_address_level:
                stats["not_verified"] += 1
                continue
            note = normalize(row[columns["비고"]])
            # Note might be a landmark description rather than a facility name.
            name = f"흡연구역 · {note}" if note else f"흡연구역 · {address}"
            lat, lng = coord
            result.append({
                "name": name, "lat": f"{lat:.8f}", "lng": f"{lng:.8f}",
                "address": address,
                "locationAccuracy": "verified" if verified else "address-level",
                "source": normalize(row[columns["출처"]]),
            })
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not result:
            raise ValueError(
                "표시 가능한 흡연구역이 없습니다. 좌표 및 '위치검증' 열을 확인하세요. "
                "주소 기반 좌표를 사용할 경우 --include-address-level을 명시하세요."
            )
        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=["name", "lat", "lng", "address", "locationAccuracy", "source"])
            writer.writeheader()
            writer.writerows(result)
        return {**stats, "exported": len(result)}
    finally:
        book.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="강남구_흡연구역_전처리.xlsx")
    parser.add_argument("--output", type=Path, required=True, help="백엔드 로딩용 CSV 파일 경로")
    parser.add_argument("--include-address-level", action="store_true",
                        help="주소 좌표(현장 미검증)도 별도 경고 표시를 전제로 내보냄")
    args = parser.parse_args()
    stats = convert(args.input, args.output, args.include_address_level)
    print(stats)
    print("지도 출처는 주소 위치 기준일 수 있으며 흡연부스의 실제 입구 위치가 아닙니다.")


if __name__ == "__main__":
    main()
