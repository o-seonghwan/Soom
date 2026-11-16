"""Explicitly configured smoking-area locations; never interpret no-smoking zones as smoking zones."""
import csv
import math
import os
from pathlib import Path


def load_smoking_zones():
    configured = os.environ.get("LUNG_SMOKING_ZONES_CSV", "").strip()
    if not configured:
        return {"source": "not-configured", "zones": []}
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"흡연구역 CSV 파일이 없습니다: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        lat_col = next((x for x in ("lat", "latitude", "위도") if x in fields), None)
        lng_col = next((x for x in ("lng", "lon", "longitude", "경도") if x in fields), None)
        name_col = next((x for x in ("name", "시설명", "흡연구역명", "명칭") if x in fields), None)
        if not lat_col or not lng_col or not name_col:
            raise ValueError("흡연구역 CSV에는 name/시설명, lat/위도, lng/경도 열이 필요합니다.")
        zones = []
        for line, entry in enumerate(reader, 2):
            name = (entry[name_col] or "").strip()
            try:
                lat = float(entry[lat_col])
                lng = float(entry[lng_col])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"흡연구역 CSV {line}행 좌표가 올바르지 않습니다.") from exc
            if not name or not all(map(math.isfinite, (lat, lng))) or not (37 <= lat <= 38 and 126 <= lng <= 128):
                raise ValueError(f"흡연구역 CSV {line}행 시설명 또는 서울권 좌표 확인 필요")
            zones.append({"id": f"smoking-zone-{line}", "name": name, "lat": lat, "lng": lng})
    return {"source": "configured-csv", "zones": zones}
