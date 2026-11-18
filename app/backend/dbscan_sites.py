"""Serve the CSV outputs produced by 4_B2G_흡연구역_입지후보.py.

The B2G feature intentionally never recomputes DBSCAN on API requests and
never manufactures candidate coordinates. Candidates require field review.
"""
import csv
import math
import os
from pathlib import Path

RESULT_DIR = Path(__file__).resolve().parents[2] / "notebooks" / "03_modeling" / "결과" / "4_입지후보"
FILES = {
    "clusters": "4_입지후보_군집.csv",
    "candidates": "4_입지후보_후보지.csv",
}
VALID_LAT = (37.0, 38.0)
VALID_LNG = (126.0, 128.0)


def _number(row, field, row_num, required=False):
    raw = str(row.get(field) or "").strip()
    if not raw:
        if required:
            raise ValueError(f"{row_num}행 '{field}' 누락")
        return None
    try:
        number = float(raw)
    except ValueError as exc:
        raise ValueError(f"{row_num}행 '{field}' 숫자 변환 실패") from exc
    if not math.isfinite(number):
        if not required and math.isnan(number):
            # pandas may export an unavailable optional metric as NaN.
            return None
        raise ValueError(f"{row_num}행 '{field}' 유한한 값이 아님")
    return number


def _rows(path, required_columns):
    if not path.is_file():
        raise FileNotFoundError(f"DBSCAN 분석 결과가 없습니다: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required_columns) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} 필수 컬럼 누락: {', '.join(sorted(missing))}")
        return list(reader)


def _point(row, line_number):
    lat = _number(row, "위도", line_number, required=True)
    lng = _number(row, "경도", line_number, required=True)
    if not (VALID_LAT[0] <= lat <= VALID_LAT[1] and VALID_LNG[0] <= lng <= VALID_LNG[1]):
        raise ValueError(f"{line_number}행 좌표가 서울권 범위를 벗어납니다")
    return lat, lng


def load_dbscan_sites():
    configured = os.environ.get("LUNG_DBSCAN_RESULTS_DIR", "").strip()
    root = Path(configured).expanduser().resolve() if configured else RESULT_DIR
    clusters_raw = _rows(root / FILES["clusters"], ("군집", "위도", "경도", "적발건수", "대표장소", "판정"))
    candidates_raw = _rows(root / FILES["candidates"], ("군집", "순위", "위도", "경도", "접근거리m(보행)", "권장 형태"))
    clusters = []
    ids = set()
    for line, row in enumerate(clusters_raw, start=2):
        cluster_id = str(row["군집"]).strip()
        if not cluster_id or cluster_id in ids:
            raise ValueError(f"{line}행 군집 ID 누락 또는 중복")
        ids.add(cluster_id)
        lat, lng = _point(row, line)
        count = _number(row, "적발건수", line, required=True)
        if count < 0 or count != int(count):
            raise ValueError(f"{line}행 적발건수 오류")
        clusters.append({
            "id": cluster_id,
            "lat": lat,
            "lng": lng,
            "representativePlace": row["대표장소"],
            "recordCount": int(count),
            "placeCount": _number(row, "장소수", line),
            "verdict": row["판정"],
            "repeatedYears": row.get("연도 반복", ""),
        })

    candidates = []
    for line, row in enumerate(candidates_raw, start=2):
        cluster_id = str(row["군집"]).strip()
        if cluster_id not in ids:
            raise ValueError(f"{line}행의 군집 ID가 군집 결과에 없습니다: {cluster_id}")
        lat, lng = _point(row, line)
        rank = _number(row, "순위", line, required=True)
        if not 1 <= rank <= 3 or rank != int(rank):
            raise ValueError(f"{line}행 후보 순위 오류")
        dist = _number(row, "접근거리m(보행)", line, required=True)
        if dist < 0:
            raise ValueError(f"{line}행 접근거리 오류")
        candidates.append({
            "id": f"{cluster_id}-{int(rank)}",
            "clusterId": cluster_id,
            "rank": int(rank),
            "lat": lat,
            "lng": lng,
            "nodeId": str(row.get("노드 ID", "")),
            "representativePlace": row.get("대표장소", ""),
            "walkingDistanceM": round(dist, 1),
            "recommendedType": row["권장 형태"],
            "exposureChange": row.get("노출 변화율(현재 대비)", ""),
            "riskProbabilityOOF": _number(row, "위험확률 OOF", line),
            "pedestrianFlowPercentile": _number(row, "보행흐름 백분위", line),
            "fieldCheck": row.get("현장 확인", ""),
        })

    candidates.sort(key=lambda row: (row["clusterId"], row["rank"]))
    return {
        "source": "dbscan-analysis-csv",
        "parameters": {
            "epsM": 30,
            "minRecords": 30,
            "accessLimitM": 200,
            "maxCandidatesPerCluster": 3,
            "origin": "notebooks/03_modeling/1_모델학습/4_B2G_흡연구역_입지후보.py",
        },
        "summary": {
            "clusterCount": len(clusters),
            "candidateCount": len(candidates),
            "reviewClusterCount": sum(c["verdict"] == "후보 검토" for c in clusters),
        },
        "clusters": clusters,
        "candidates": candidates,
        "disclaimer": "현장 확인 전 입지 후보이며 설치 허가·적법성 또는 실제 노출 감소가 검증된 위치가 아닙니다.",
    }
