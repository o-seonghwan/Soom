"""Read model 1's point-risk CSV without changing its meaning.

위험점수 is a percentile rank of enforcement-record proximity predictions,
NOT an observed secondhand-smoke exposure probability.
"""
import csv
import math
from pathlib import Path

REQUIRED_COLUMNS = ("노드 ID", "위도", "경도", "위험점수")
DEFAULT_RADIUS_M = 21.0


def load_model_risks(csv_path, radius_m=DEFAULT_RADIUS_M):
    """Convert model output to the risk-location schema expected by FastAPI.

    Explicitly fail on missing, malformed or empty input. Never silently
    substitute mock risk locations for a requested model file.
    """
    source = Path(csv_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"모델 위험지도 CSV가 없습니다: {source}")

    radius = float(radius_m)
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("모델 위험 영향 반경은 유한한 양수여야 합니다.")

    locations = []
    seen = set()
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"모델 위험지도 CSV의 필수 컬럼이 없습니다: {sorted(missing)}")

        for row_number, row in enumerate(reader, start=2):
            try:
                node = (row["노드 ID"] or "").strip()
                lat = float(row["위도"])
                lng = float(row["경도"])
                score = float(row["위험점수"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"모델 CSV {row_number}행의 식별자/좌표/점수가 잘못되었습니다.") from exc

            if not node:
                raise ValueError(f"모델 CSV {row_number}행에 노드 ID가 없습니다.")
            if node in seen:
                raise ValueError(f"모델 CSV 노드 ID 중복: {node}")
            seen.add(node)

            if not (math.isfinite(lat) and math.isfinite(lng) and math.isfinite(score)):
                raise ValueError(f"모델 CSV {row_number}행에 비유한 숫자가 있습니다.")
            if not (-90 <= lat <= 90 and -180 <= lng <= 180 and 0 <= score <= 100):
                raise ValueError(f"모델 CSV {row_number}행의 좌표 또는 위험점수가 범위를 벗어났습니다.")

            locations.append({
                "id": f"model-node-{node}",
                "lat": lat,
                "lng": lng,
                "score": score,
                "radiusM": radius,
            })

    if not locations:
        raise ValueError("모델 위험지도 CSV가 비어 있습니다.")
    return locations
