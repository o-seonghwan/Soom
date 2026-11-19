"""Read the existing offline childcare exposure ranking CSV. No inferred/modelled rows."""
import csv
import math
import os
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "notebooks" / "03_modeling" / "결과" / "3_어린이집_노출순위.csv"
REQUIRED = ("어린이집명", "유형", "주소", "현원", "위도", "경도", "주변지점수",
            "주변_최고위험점수", "주변_평균위험점수", "주변_상위10%지점수", "노출점수", "우선순위")


def _number(row, key, index, integer=False, required=True):
    value = (row.get(key) or "").strip()
    if not value:
        if required:
            raise ValueError(f"{index}행 {key} 값이 없습니다.")
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{index}행 {key} 값이 숫자가 아닙니다.") from exc
    if not math.isfinite(number):
        if not required and math.isnan(number):
            return None
        raise ValueError(f"{index}행 {key} 값이 유효하지 않습니다.")
    if integer and (number < 0 or not number.is_integer()):
        raise ValueError(f"{index}행 {key} 값은 0 이상의 정수여야 합니다.")
    return int(number) if integer else number


def load_childcare_exposure():
    configured = os.environ.get("LUNG_CHILDCARE_EXPOSURE_CSV", "").strip()
    path = Path(configured).expanduser().resolve() if configured else DEFAULT_CSV
    if not path.is_file():
        raise FileNotFoundError(
            f"어린이집 노출순위 CSV가 없습니다: {path}. "
            "03_modeling/2_서비스/3_B2G_비흡연자_아동간접흡연보호리포트.py로 생성하거나 "
            "LUNG_CHILDCARE_EXPOSURE_CSV를 설정하세요."
        )
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(REQUIRED) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"어린이집 CSV 필수 컬럼 누락: {', '.join(sorted(missing))}")
        rows = list(reader)

    nurseries = []
    for index, row in enumerate(rows, start=2):
        lat = _number(row, "위도", index)
        lng = _number(row, "경도", index)
        if not (37 <= lat <= 38 and 126 <= lng <= 128):
            raise ValueError(f"{index}행 어린이집 좌표가 서울권 범위 밖입니다.")
        name = (row["어린이집명"] or "").strip()
        if not name:
            raise ValueError(f"{index}행 어린이집명이 비어 있습니다.")
        rank = _number(row, "우선순위", index, integer=True)
        if rank < 1:
            raise ValueError(f"{index}행 우선순위는 1 이상이어야 합니다.")
        nurseries.append({
            "id": str(index),
            "name": name,
            "type": (row["유형"] or "").strip(),
            "address": (row["주소"] or "").strip(),
            "enrollment": _number(row, "현원", index, integer=True),
            "lat": lat, "lng": lng,
            "nearbyPointCount": _number(row, "주변지점수", index, integer=True),
            "nearbyMaxRisk": _number(row, "주변_최고위험점수", index, required=False),
            "nearbyMeanRisk": _number(row, "주변_평균위험점수", index, required=False),
            "highRiskPointCount": _number(row, "주변_상위10%지점수", index, integer=True),
            "exposureScore": _number(row, "노출점수", index),
            "priorityRank": rank,
        })
    nurseries.sort(key=lambda x: (x["priorityRank"], -x["enrollment"], x["name"]))
    return {
        "source": "childcare-exposure-csv",
        "analysisRadiusM": 100,
        "summary": {
            "nurseryCount": len(nurseries),
            "withHighRiskPoints": sum(n["highRiskPointCount"] > 0 for n in nurseries),
        },
        "nurseries": nurseries,
        "disclaimer": (
            "보행 지점의 AI 상대 위험점수를 활용한 어린이집 주변 100m 참고 지표입니다. "
            "실제 흡연 발생·실측 연기 농도·아동 개인 노출을 의미하지 않습니다. "
            "동점 순위가 존재할 수 있으며 현장 확인이 필요합니다."
        ),
    }
