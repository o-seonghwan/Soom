# AI 위험지도 → 청정지수 연동 (실험용 v1)

## 목적과 해석

현행 `main`의 `notebooks/03_modeling/1_모델학습/1_B2C_비흡연자_간접흡연위험지도.py` 결과 CSV를 FastAPI에 연결합니다.
이 모델의 `위험점수`(0~100)는 **강남구 내 꽁초 적발 기록과의 근접성에 관한 상대적 예측 위험 순위**입니다. 실측 담배 연기 농도나 개인 노출 확률이 아닙니다.

- API의 기존 `score`: 위험점수(높을수록 회피 대상)
- 새 `cleanIndex`: **100 - 유효 위험점수**, 높을수록 상대적으로 청정하다는 *파생 지표*
- **모델이 직접 청정지수를 예측하는 것이 아님**: 모델의 위험점수에서 별도 계산함.
- **표시 UI는 아직 변경하지 않음**: API 데이터에 `cleanIndex`만 추가. 지도 범례·색상·프론트엔드 UI는 추후 결정.
- `cleanIndex=100`은 이 모델에 의한 위험 기여도가 0이라는 뜻이며, 공기가 실제로 안전하다는 보장은 아님.

## 거리별 임시 감쇠 설정 (추후 조정 대상)

보행 링크의 선형(geometry)과 모델 예측 지점 사이 **최소 직선거리(m)**를 계산하여 상대 위험 기여를 적용합니다.

| 거리 | 위험점수 반영 비율 | 예: 모델 위험점수 80 | 청정지수(100-위험기여) |
|---|---:|---:|---:|
| 0~10m (포함) | 100% | 80 | 20 |
| 10m 초과~15m (포함) | **65%** | 52 | 48 |
| 15m 초과~21m (포함) | **30%** | 24 | 76 |
| 21m 초과 | 0% | 0 | 100 |

값은 `app/backend/risk_decay.py`의 `DISTANCE_BANDS`에서 변경할 수 있습니다. 값들은 현장 검증으로 얻은 감쇠율이 아니라 **임의의 임시 서비스 정책**입니다. 경계에서는 계단형으로 변하며, 실제 대기 확산 법칙을 대변하지 않습니다.

여러 모델 예측 지점이 같은 보행 링크에 영향을 주면 **가장 높은 거리 보정 위험 기여점수**를 적용합니다. 기존 `normalizedRisk`와 A* 회피 비용은 이 보정 위험을 활용합니다. 경로의 임시 출발·도착 링크도 같은 거리 감쇠를 사용합니다. 링크 일부가 예측 지점에 가까우면 **링크 전체에 가까운 부분의 최대 위험도가 적용**되므로 보수적인 근사이며, 긴 링크에 대해서는 추후 구간별 적분 방식이 필요합니다.

## 실행 (현재 모델링 폴더 구조)

1. 모델 전처리·학습:

```powershell
python notebooks/03_modeling/1_모델학습/0_머신러닝_전처리.py
python notebooks/03_modeling/1_모델학습/0_공간5Fold_분할.py
python notebooks/03_modeling/1_모델학습/1_B2C_비흡연자_간접흡연위험지도.py
```

2. 저장된 `notebooks/03_modeling/결과/전처리기반/1_위험지도_지점.csv`의 경로를 지정. 백엔드 실행 **동일 터미널**에서:

```powershell
$repo = (git rev-parse --show-toplevel).Trim()
$env:LUNG_RISK_CSV = Join-Path $repo "notebooks/03_modeling/결과/전처리기반/1_위험지도_지점.csv"
cd app/backend
python -m uvicorn main:app --reload
```

보행 그래프 `data/processed/walking_network/gangnam_walk.graphml`도 미리 준비되어야 합니다(`app/backend/download_network.py`).

3. API 확인:
- `GET /api/health` → `risk_source: model-csv`
- `GET /api/risks` → 모델 지점별 `score`, `cleanIndex`, `radiusM:21` (`score`는 감쇠 전 원점수)
- `GET /api/risks/edges` → 거리 감쇠 후 링크별 `score`, `cleanIndex`, `normalizedRisk`
- `POST /api/routes` → 감쇠 후 위험 비용으로 회피 경로 계산

`LUNG_RISK_CSV`가 없으면 기존 Mock 로직 그대로 작동합니다. **경로를 지정했지만 파일이 없거나 데이터가 잘못되면 오류를 표시하며 Mock으로 조용히 대체하지 않습니다.** 위경도는 서울 근방(위도 37~38, 경도 126~128)과 점수(0~100)를 검증합니다.

> 주의: `LUNG_RISK_CSV`는 모델 CSV 파일의 정확한 전체 경로입니다. `LUNG_DATA_ROOT`와 `LUNG_EDA_ROOT`는 모델 학습용 **입력** 데이터 폴더 설정입니다.

## 테스트

```powershell
python -m unittest discover -s app/backend -p "test_model_risk_integration.py" -v
```

GitHub Actions에서 위 회귀 테스트와 문법/프론트엔드 빌드를 검사합니다. **실제 전체 모델 학습, 대규모 OSM 그래프 결합, 경로 차이 정량 검증은 아직 별도 수행이 필요합니다.**

## 추후 결정할 사항
- 지도에 청정지수를 표시하는 위치·색상·범례·숫자 형식
- 65% / 30% 감쇠율 및 21m 이후 잔여 영향의 과학적·현장 타당성
- 보행 링크 길이에 따른 구간별 위험도 평균과 다중 예측 지점 합성
- 청정지수 정규화 및 유효 위험점수 외의 공기질·실측 신호 연동
