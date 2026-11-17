"""강남구 흡연구역 엑셀의 중복을 합치고 VWorld 주소 좌표를 붙인다.

실행: python 0_강남구_흡연구역_전처리.py [입력.xlsx] [--output 결과.xlsx]
입력을 생략하면 LUNG_DATA_ROOT 및 프로젝트 상위 폴더에서 원본을 찾는다.
기존 좌표는 기본으로 보존한다. --refresh는 주소 기준 좌표로 다시 조회한다.
좌표는 WGS84 위도, 경도 순서이며 개별 부스가 아닌 주소의 좌표일 수 있다.
"""
import argparse
import os
from collections import defaultdict
from pathlib import Path
import re
import tempfile
from time import sleep
import unicodedata

import requests
from openpyxl import load_workbook


FILENAME = "강남구_흡연구역.xlsx"
ADDRESS = "주소"
COORD = "좌표"
NOTE = "비고"
SOURCE = "출처"
METADATA = ("구", "공공/민간", "시설형태", "담당기관", "담당번호")


def text(value):
    return "" if value is None else str(value).strip()


def normalize(value):
    return re.sub(r"[^\w-]", "", unicodedata.normalize("NFKC", text(value)).casefold())


def address_key(value):
    address = re.sub(r"^서울(?:특별시|시)?\s*", "", text(value))
    return normalize(address)


def default_input():
    roots = list(Path(__file__).resolve().parents)
    if os.getenv("LUNG_DATA_ROOT"):
        roots.insert(0, Path(os.environ["LUNG_DATA_ROOT"]).expanduser())
    for root in roots:
        for folder in (root, root / "분석데이터_머신러닝",
                       root / "02_1_분석데이터" / "분석데이터_머신러닝"):
            path = folder / FILENAME
            if path.is_file():
                return path
    raise SystemExit(f"{FILENAME}를 찾지 못했습니다. 입력 파일 경로를 인수로 지정하세요.")


def api_key(input_path):
    value = text(os.getenv("VWORLD_API_KEY"))
    if value:
        return value
    folders = [*Path(__file__).resolve().parents, *input_path.parents,
               Path.home() / "Downloads", Path.home() / "다운로드"]
    for folder in dict.fromkeys(folders):
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8-sig").splitlines():
                name, separator, value = line.removeprefix("export ").partition("=")
                if separator and name.strip() == "VWORLD_API_KEY":
                    value = value.strip().strip('"').strip("'")
                    if value:
                        return value
    raise SystemExit("환경 변수 또는 .env에 VWORLD_API_KEY를 설정하세요.")


def lookup(session, address, key):
    address_types = ("road", "parcel") if re.search(r"(로|길)\s+\d", address) else ("parcel", "road")
    for address_type in address_types:
        try:
            response = session.get("https://api.vworld.kr/req/address", timeout=10, params={
                "service": "address", "request": "getcoord", "version": "2.0",
                "crs": "epsg:4326", "address": address, "refine": "true",
                "simple": "false", "format": "json", "type": address_type, "key": key,
            })
            response.raise_for_status()
            result = response.json()["response"]
            if result["status"] == "NOT_FOUND":
                continue
            if result["status"] != "OK":
                raise RuntimeError("VWorld 응답 오류. 키 설정과 호출 한도를 확인하세요.")
            point = result["result"]["point"]
            latitude, longitude = float(point["y"]), float(point["x"])
            if 37.44 <= latitude <= 37.54 and 127.00 <= longitude <= 127.15:
                return f"{latitude:.8f}, {longitude:.8f}"
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            raise RuntimeError(f"VWorld 호출 실패 ({type(error).__name__})") from None
        finally:
            sleep(0.15)
    return None


def same_facility(first, second, columns):
    # 주소 좌표는 여러 시설에서 같을 수 있으므로 중복 판정에는 쓰지 않는다.
    # 같은 동·층·출입구 설명이 있어야 합치며, 시설 속성이 서로 다르면 보존한다.
    note = normalize(first[columns[NOTE]])
    if not note or note != normalize(second[columns[NOTE]]):
        return False
    return all(
        not text(first[columns[name]]) or not text(second[columns[name]])
        or normalize(first[columns[name]]) == normalize(second[columns[name]])
        for name in METADATA if name in columns
    )


def deduplicate(sheet, columns):
    groups = defaultdict(list)
    deleted = []
    for number, values in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
        row = list(values)
        address = text(row[columns[ADDRESS]])
        if not address or address_key(address) == "강남구":
            continue
        candidates = groups[address_key(address)]
        matches = [(index, prior) for index, prior in candidates if same_facility(prior, row, columns)]
        if len(matches) != 1:
            candidates.append((number, row))
            continue

        target, prior = matches[0]
        source_col = columns[SOURCE]
        sources = (text(prior[source_col]), text(row[source_col]))
        names = dict.fromkeys(
            name.strip() for source in sources for name in re.split(r"\s+/\s+|[\n;]+", source)
            if name.strip()
        )
        if names:
            prior[source_col] = " / ".join(names)
        for col, value in enumerate(row):
            if not text(prior[col]) and text(value):
                prior[col] = value
        for col, value in enumerate(prior, 1):
            sheet.cell(target, col).value = value
        deleted.append(number)

    for number in reversed(deleted):
        sheet.delete_rows(number)
    return len(deleted)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--refresh", action="store_true", help="기존 좌표도 VWorld 주소로 재조회")
    args = parser.parse_args()
    source = (args.input or default_input()).resolve()
    output = (args.output or source.with_name(f"{source.stem}_전처리.xlsx")).resolve()
    if output == source:
        parser.error("결과 파일은 원본과 다른 경로를 지정하세요.")
    if source.suffix.lower() != ".xlsx" or output.suffix.lower() != ".xlsx":
        parser.error("입력과 출력은 .xlsx 파일이어야 합니다.")

    book = load_workbook(source)
    sheet = book.active
    columns = {text(cell.value): cell.column - 1 for cell in sheet[1]}
    missing = {ADDRESS, COORD, NOTE, SOURCE} - columns.keys()
    if missing:
        parser.error("필수 열 누락: " + ", ".join(sorted(missing)))

    merged = deduplicate(sheet, columns)
    cache = {}
    filled = failures = 0
    try:
        with requests.Session() as session:
            for row in sheet.iter_rows(min_row=2):
                address = text(row[columns[ADDRESS]].value)
                if not address or address_key(address) == "강남구":
                    continue
                coordinate = row[columns[COORD]]
                if text(coordinate.value) and not args.refresh:
                    continue
                normalized = address_key(address)
                if normalized not in cache:
                    if not cache:
                        key = api_key(source)
                    cache[normalized] = lookup(session, address, key)
                value = cache[normalized]
                if value is None:
                    print(f"좌표 미확인: {address} ({text(row[columns[NOTE]].value)})")
                    failures += 1
                else:
                    coordinate.value = value
                    filled += 1
    except RuntimeError as error:
        raise SystemExit(str(error)) from None

    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".xlsx", delete=False) as file:
        temporary = Path(file.name)
    try:
        book.save(temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"중복 병합 {merged}행, VWorld 좌표 기록 {filled}행, 미확인 {failures}행")
    print(f"저장 위치: {output}")


if __name__ == "__main__":
    main()
