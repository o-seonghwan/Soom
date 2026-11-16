
from datetime import datetime, timezone


# =====================================================
# 1. Mock 위험도 데이터
# =====================================================

# 강남역 인근 테스트 위치
# 실제 흡연 발생 위험도를 나타내지 않음
MOCK_RISKS = [
    {
        "id": "risk-1",
        "lat": 37.4985,
        "lng": 127.0280,
        "score": 90,
        "radiusM": 35,
    },
    {
        "id": "risk-2",
        "lat": 37.4995,
        "lng": 127.0300,
        "score": 55,
        "radiusM": 35,
    },
    {
        "id": "risk-3",
        "lat": 37.4965,
        "lng": 127.0260,
        "score": 15,
        "radiusM": 35,
    },
]


# =====================================================
# 2. 위험도 데이터 검증
# =====================================================

def validate_risk(risk):
    """
    위험도 데이터를 내부 표준 형식으로 변환한다.

    score: 0~100
    radiusM: 미터 단위
    """

    score = float(risk["score"])
    radius = float(risk["radiusM"])
    lat = float(risk["lat"])
    lng = float(risk["lng"])

    if not 0 <= score <= 100:
        raise ValueError(
            "위험점수는 0~100 사이여야 합니다."
        )

    if radius <= 0:
        raise ValueError(
            "위험 반경은 0보다 커야 합니다."
        )

    if not (-90 <= lat <= 90):
        raise ValueError("위도 범위가 잘못되었습니다.")

    if not (-180 <= lng <= 180):
        raise ValueError("경도 범위가 잘못되었습니다.")

    return {
        "id": str(risk["id"]),
        "lat": lat,
        "lng": lng,
        "score": score,
        "radiusM": radius,
    }


# =====================================================
# 3. 위험도 데이터 공급자
# =====================================================

def get_risk_snapshot():
    """
    현재 사용할 위험도 데이터 묶음 반환.

    11단계: Mock 데이터
    추후: AI 모델 예측 결과 또는 DB 조회
    """

    locations = [
        validate_risk(risk)
        for risk in MOCK_RISKS
    ]

    return {
        "source": "mock",
        "version": "mock-v1",
        "generatedAt": datetime.now(
            timezone.utc
        ).isoformat(),
        "locations": locations,
    }
