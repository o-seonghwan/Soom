# B2G AI 모델 청정지수 지도 — 보행로 색상형

이 브랜치는 실제 `notebooks/03_modeling/결과/전처리기반/1_위험지도_지점.csv`를 사용할 때만 B2G 청정지수 지도를 그립니다. **Mock 값으로 청정도 지도를 표시하지 않습니다.** B2C 화면 및 기존 API의 Mock 폴백은 바꾸지 않았습니다.

## 데이터 파이프라인

1. 모델 `위험점수`(0~100, 상대 위험 순위)를 `model_risk_adapter.py`가 읽음
2. `risk_mapper.py`에서 모델 예측 지점~보행 링크 최단 직선거리별 위험을 보정
   - 0~10m 100%, 10~15m 65%, 15~21m 30%, 21m 초과 0%
3. 보행 링크별 `cleanIndex = 100 - effectiveRisk`를 `/api/b2g/cleanliness/edges` GeoJSON으로 제공
4. B2G 화면에서 보행로 색상형으로 표시

**주의:** 청정지수는 실측 공기질이 아닌 모델 예측 위험 순위로 만든 파생 지표이며, 계산되지 않은 보행로는 데이터 없음이지 청정 100이라는 뜻이 아닙니다.

## Windows PowerShell 실행

```powershell
git fetch origin
git switch feature/b2g-cleanliness-roads
$repo = (git rev-parse --show-toplevel).Trim()
$env:LUNG_RISK_CSV = Join-Path $repo "notebooks/03_modeling/결과/전처리기반/1_위험지도_지점.csv"
Test-Path $env:LUNG_RISK_CSV
cd app/backend
python -m uvicorn main:app --reload
```

`Test-Path`가 `True`여야 합니다. CSV가 없다면 새 모델링 구조의 전처리와 학습을 실행하여 먼저 생성해야 합니다. 백엔드 시작 전 강남 보행 GraphML도 준비해야 합니다.

다른 PowerShell 터미널에서는 `app/frontend`에서 `npm ci` (최초 1회), `npm run dev`를 실행합니다.

검증:

```powershell
(Invoke-RestMethod http://localhost:8000/api/health).risk_source
$data = Invoke-RestMethod http://localhost:8000/api/b2g/cleanliness/edges
$data.source
$data.modelPointCount
$data.features.Count
```

정상이라면 `risk_source`와 `$data.source`는 모두 `model-csv`여야 하며, `features`에는 실제 위험도가 매핑된 보행 링크만 포함됩니다. 환경변수를 설정하지 않은 경우 B2G 청정지수 API는 HTTP 503을 반환하며 Mock 청정도 지도는 그리지 않습니다.

실제 모델 결과 CSV와 전체 보행망을 이용한 브라우저 End-to-End/성능 검증은 별도로 필요합니다.


## B2G/B2C 보행로 시각화 투명도 정책 (비교안 A, 임시)

- B2G: 기존 청정지수 5단계 색상을 유지하고 보행로 `opacity=0.36`으로 반투명 표현합니다. 히트맵처럼 주변 공간에 퍼지는 효과는 아니며 **보행로 선형만** 표시합니다.
- B2C: 같은 모델 기반 보행 링크 GeoJSON을 사용하며 보행로 색은 연두색 `#84cc16`으로 통일합니다. `opacity = 0.18 + 0.67 * (cleanIndex / 100)`을 적용합니다. 따라서 **청정지수가 낮을수록 투명도가 높고(연하게 표시), 높을수록 투명도가 낮습니다**.
- B2C 예시: 청정지수 0 → 불투명도 0.18, 50 → 0.515, 100 → 0.85.
- B2G/B2C 모두 CSV가 없으면 모델 지수 보행로를 그리지 않으며 Mock 데이터로 대체하지 않습니다. 모델을 읽을 때는 `LUNG_RISK_CSV` 설정이 필요합니다.
- 기존 출발지·도착지·A* 경로·신고 마커 등은 유지합니다. B2C의 기존 원형 위험 마커는 보행로 지수가 연결된 상태에서 중복으로 표시하지 않습니다.
- 거리 감쇠(0~10m 100%, 10~15m 65%, 15~21m 30%)는 **변경하지 않았습니다.** 이번 작업은 시각화 투명도 변경입니다.
- 별도 `feature/b2g-cleanliness-heatmap` 브랜치는 변경하지 않았습니다.
