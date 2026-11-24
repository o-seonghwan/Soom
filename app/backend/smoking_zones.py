"""Explicitly configured smoking-area locations; never interpret no-smoking zones as smoking zones."""
import csv
import math
import os
from pathlib import Path


# Resolve from this Python file, not the process working directory.
# Supports local Windows paths containing spaces and Korean characters.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Bundled source records are marked as unverified; never call them verified facilities.
# The backend Docker image includes app/backend/data, so this works on Railway
# even if the optional volume path has not been configured.
DEFAULT_SMOKING_ZONES_CSV = Path(__file__).resolve().parent / "data" / "gangnam_smoking_zones.csv"


def _resolve_smoking_csv():
    configured = os.environ.get("LUNG_SMOKING_ZONES_CSV", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return path
        # The legacy sample path may persist in a different shell or .env.
        # Fall back ONLY to the exact Gangnam smoking-zones output, never
        # to enforcement, litter, no-smoking, or other datasets.
        if DEFAULT_SMOKING_ZONES_CSV.is_file():
            return DEFAULT_SMOKING_ZONES_CSV
        raise FileNotFoundError(
            f"흡연구역 CSV 파일이 없습니다: {path}. "
            f"프로젝트 기본 경로도 확인하세요: {DEFAULT_SMOKING_ZONES_CSV}"
        )
    if DEFAULT_SMOKING_ZONES_CSV.is_file():
        return DEFAULT_SMOKING_ZONES_CSV
    return None


def load_smoking_zones():
    path = _resolve_smoking_csv()
    if path is None:
        return {"source": "not-configured", "zones": []}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        lat_col = next((x for x in ("lat", "latitude", "위도") if x in fields), None)
        lng_col = next((x for x in ("lng", "lon", "longitude", "경도") if x in fields), None)
        name_col = next((x for x in ("name", "시설명", "흡연구역명", "명칭") if x in fields), None)
        if not lat_col or not lng_col or not name_col:
            raise ValueError("흡연구역 CSV에는 name/시설명, lat/위도, lng/경도 열이 필요합니다.")
        zones = []
        accuracy_col = "locationAccuracy" if "locationAccuracy" in fields else None
        address_col = "address" if "address" in fields else None
        source_col = "source" if "source" in fields else None
        for line, entry in enumerate(reader, 2):
            name = (entry[name_col] or "").strip()
            try:
                lat = float(entry[lat_col])
                lng = float(entry[lng_col])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"흡연구역 CSV {line}행 좌표가 올바르지 않습니다.") from exc
            if not name or not all(map(math.isfinite, (lat, lng))) or not (37 <= lat <= 38 and 126 <= lng <= 128):
                raise ValueError(f"흡연구역 CSV {line}행 시설명 또는 서울권 좌표 확인 필요")
            accuracy = (entry.get(accuracy_col) or "").strip() if accuracy_col else "unspecified"
            if accuracy not in {"verified", "address-level", "unspecified"}:
                raise ValueError(f"흡연구역 CSV {line}행 위치 정확도 값 확인 필요")
            zones.append({
                "id": f"smoking-zone-{line}", "name": name, "lat": lat, "lng": lng,
                "locationAccuracy": accuracy,
                "address": (entry.get(address_col) or "").strip() if address_col else "",
                "source": (entry.get(source_col) or "").strip() if source_col else "",
            })
    return {"source": "configured-csv", "zones": zones}
