# B2G AI 모델 청정지수 지도 — 반투명 히트맵형

이 브랜치는 실제 `notebooks/03_modeling/결과/전처리기반/1_위험지도_지점.csv`를 사용할 때만 B2G 청정지수 지도를 그립니다. **Mock 값으로 청정도 지도를 표시하지 않습니다.** B2C 화면 및 기존 API의 Mock 폴백은 바꾸지 않았습니다.

## 데이터 파이프라인

1. 모델 `위험점수`(0~100, 상대 위험 순위)를 `model_risk_adapter.py`가 읽음
2. `risk_mapper.py`에서 모델 예측 지점~보행 링크 최단 직선거리별 위험을 보정
   - 0~10m 100%, 10~15m 65%, 15~21m 30%, 21m 초과 0%
3. 보행 링크별 `cleanIndex = 100 - effectiveRisk`를 `/api/b2g/cleanliness/edges` GeoJSON으로 제공
4. B2G 화면에서 반투명 히트맵형으로 표시

**주의:** 청정지수는 실측 공기질이 아닌 모델 예측 위험 순위로 만든 파생 지표이며, 계산되지 않은 보행로는 데이터 없음이지 청정 100이라는 뜻이 아닙니다.

## Windows PowerShell 실행

```powershell
git fetch origin
git switch feature/b2g-cleanliness-heatmap
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
