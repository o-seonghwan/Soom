"""Model risk-score interpretation and provisional spatial falloff.

The trained model emits a *relative risk rank* in 0..100, not measured
secondhand smoke concentration or probability. Distance bands are design
assumptions subject to later validation; zero contribution beyond 21m
does NOT mean the location is scientifically proven smoke-free.
"""
import math

MODEL_RADIUS_M = 21.0
DISTANCE_BANDS = (
    (10.0, 1.00),
    (15.0, 0.65),
    (21.0, 0.30),
)


def risk_multiplier(distance_m):
    """Multiplier at the minimum straight-line distance to a modeled site."""
    distance = float(distance_m)
    if not math.isfinite(distance) or distance < 0:
        raise ValueError("거리에는 0 이상의 유한한 숫자가 필요합니다.")
    for upper_m, multiplier in DISTANCE_BANDS:
        if distance <= upper_m:
            return multiplier
    return 0.0


def effective_risk(model_risk_score, distance_m):
    """Return a modeled contribution on a 0..100 risk scale."""
    score = float(model_risk_score)
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("모델 위험점수는 0~100 사이의 유한한 숫자여야 합니다.")
    return score * risk_multiplier(distance_m)


def cleanliness_index(effective_risk_score):
    """Risk-derived provisional clean index (100 is cleaner, 0 is riskier)."""
    score = float(effective_risk_score)
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("유효 위험점수는 0~100 사이의 유한한 숫자여야 합니다.")
    return 100.0 - score
