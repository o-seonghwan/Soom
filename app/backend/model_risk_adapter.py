"""Strict adapter for the current notebooks/03_modeling risk-point CSV.

Input: 결과/전처리기반/1_위험지도_지점.csv
Required columns: 노드 ID, 위도, 경도, 위험점수.
The model score is a *relative risk percentile*, not a direct measured
smoke-exposure probability or a measured air-cleanliness index.
"""
import csv
import math
from pathlib import Path

from risk_decay import MODEL_RADIUS_M, cleanliness_index


def load_model_risks(csv_path):
    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"모델 위험지도 CSV를 찾지 못했습니다: {path}")
    locations = []
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {"노드 ID", "위도", "경도", "위험점수"}
        missing = expected - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"모델 CSV 필수 열 누락: {', '.join(sorted(missing))}")
        for line_no, row in enumerate(reader, start=2):
            node_id = (row["노드 ID"] or "").strip()
            if not node_id or node_id in seen:
                raise ValueError(f"모델 CSV {line_no}행: 빈 값 또는 중복 노드 ID")
            seen.add(node_id)
            try:
                lat = float(row["위도"])
                lng = float(row["경도"])
                score = float(row["위험점수"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"모델 CSV {line_no}행: 좌표/점수 숫자 변환 실패") from exc
            if not all(map(math.isfinite, (lat, lng, score))):
                raise ValueError(f"모델 CSV {line_no}행: NaN/무한대 불가")
            if not 37.0 <= lat <= 38.0 or not 126.0 <= lng <= 128.0:
                raise ValueError(f"모델 CSV {line_no}행: 서울권 밖 좌표")
            if not 0 <= score <= 100:
                raise ValueError(f"모델 CSV {line_no}행: 위험점수 범위 초과")
            locations.append({
                "id": f"model-{node_id}",
                "lat": lat,
                "lng": lng,
                "score": score,
                "cleanIndex": cleanliness_index(score),
                "radiusM": MODEL_RADIUS_M,
                "decayProfile": "model-v1",
            })
    if not locations:
        raise ValueError(f"모델 CSV에 데이터 행이 없습니다: {path}")
    return locations
