"""Model risk-score interpretation and provisional spatial falloff.

The trained model emits a *relative risk rank* in 0..100, not measured
secondhand smoke concentration or probability.

Distance bands stay at 0–10, 10–15, and 15–21 m for service compatibility.
Band weights are derived from mean outdoor tobacco smoke (OTS) PM2.5
increments reported by Kim & Lee (2024), Nicotine & Tobacco Research,
doi:10.1093/ntr/ntad241: 6 m 12.90, 12 m 4.86, 15 m 2.78,
18 m 2.09, 21 m 1.57 micrograms/m^3.

The 6 m mean is the reference (100%). For the middle and outer bands,
we average the observed means at 12/15 m and 18/21 m respectively,
then divide by the 6 m mean. These band assignments and the constant
0–10 m weight are service assumptions, NOT weights validated in the
paper. Distances below 6 m and beyond 21 m were not measured. Zero
contribution beyond 21 m is a model coverage cutoff, NOT evidence
that outdoor tobacco smoke is absent there.
"""
import math

MODEL_RADIUS_M = 21.0

# Keep the original 3 bands; only the risk multipliers change.
_REFERENCE_OTS_PM25 = 12.90
DISTANCE_BANDS = (
    (10.0, 1.00),
    (15.0, ((4.86 + 2.78) / 2) / _REFERENCE_OTS_PM25),
    (21.0, ((2.09 + 1.57) / 2) / _REFERENCE_OTS_PM25),
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
