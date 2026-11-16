# 모델 위험지도 ↔ FastAPI/보행 네트워크 연동

이 문서는 `feature/model-integration` 브랜치의 **선택적 모델 결과 연결**을 설명합니다.
기존 B2C/B2G UI와 Mock 기본 동작을 변경하지 않습니다.

## 1. 생활인구 전처리 입력

- EDA 노트북: `notebooks/01_eda/EDA_LOCAL_RESD_250M_20261027.ipynb`, `...28.ipynb`, `...29.ipynb`
- 노트북 출력 기본 위치: **저장소의 상위** `data/processed_data/local_resd_250m[_(날짜)]/features.csv`
- 모델 `공통.py`의 `use_preprocessed_data()`는 기존 `data/processed/전처리결과`, `data/processed/EDA결과`와 상위 `data/processed_data`를 확인합니다. 또는 `LUNG_EDA_ROOT`로 출력 최상위 경로를 지정할 수 있습니다.
- **반드시 2026-10-27/28/29 세 날짜**가 있어야 합니다. 중복된 날짜별 `features.csv`, 누락 일자, 중복 `일자+시간+격자+행정동` 복합키는 오류입니다.
- 날짜/시간/격자/행정동 식별자 정규화, `*` → 결측 처리(임의 최소값/0 대체하지 않음)를 적용합니다.

`LUNG_DATA_ROOT`는 전처리본에서 누락된 상가·버스·금연구역 등 **원본**을 찾는 폴더입니다. 별도 설정이 필요할 수 있습니다. 모델이 처리할 원본의 실제 위치를 확인하세요.

## 2. 모델 결과 CSV 생성

프로젝트에 필요한 데이터와 Python 의존성이 갖춰진 상태에서 아래 순서로 실행합니다.

```powershell
# 저장소 루트 기준
python notebooks/02_preprocessing/0_머신러닝_전처리.py
python notebooks/03_modeling/1_B2C_비흡연자_간접흡연위험지도.py
```

기본 모델 출력은 `data/processed/결과/전처리기반/1_위험지도_지점.csv`입니다.
`LUNG_OUT_DIR`를 지정했다면 그 폴더의 `전처리기반` 아래에 생성됩니다.
생성 파일에는 `노드 ID`, `위도`, `경도`, `위험점수`가 있어야 합니다.

**주의:** `위험점수`는 모델의 꽁초 적발 장소 근접도 예측값으로 만든 *지역 내 상대 순위(백분위)*입니다. 실측 간접흡연 노출 확률이 아닙니다. 실험 평가 및 보행 경로 위험 가중치를 다르게 해석하면 안 됩니다.

## 3. FastAPI에서 모델 결과 사용

기본은 Mock 위험 위치 3개입니다. 모델 결과 CSV가 준비되면 **서버 실행 전에** 다음을 지정합니다.

```powershell
# 저장소 루트에서 실행 (PowerShell)
$env:LUNG_RISK_CSV = "data/processed/결과/전처리기반/1_위험지도_지점.csv"
cd app/backend
uvicorn main:app --reload
```

`LUNG_RISK_CSV`는 절대경로도 지원합니다. 변수에 설정된 파일이 없거나 형식 오류가 있으면 서버 시작이 실패하며 임의로 Mock 데이터로 대체하지 않습니다.

서버 시작 시 CSV → 모델 위험 위치(기본 반경 **21m**) → 보행망 공간 링크 매핑을 수행합니다. 지도가 보행 링크에 **한 개도 연결되지 않으면 오류**를 반환합니다. 모델 노드 ID와 OSMnx 그래프 ID가 달라도 위치(좌표)를 기준으로 연결합니다.

## 4. 검증

```powershell
# 라이브러리 의존성 없는 CSV 변환 테스트
cd app/backend
python -m unittest -v test_risk_csv_adapter.py

# 데이터 로더는 numpy, pandas 설치 후 별도 실행
cd ../../notebooks/03_modeling
python -m unittest -v test_population_loader.py
```

서버 실행 후 `GET /api/health`에서 `risk_source`가 `model-csv`인지, `GET /api/risks`와 `GET /api/risks/edges`의 반환 위치·링크 개수가 예상과 일치하는지 확인하세요.

## 5. 현재 남은 작업

- 실제 생성된 모델 CSV, 도보 `.graphml` 파일과 원자료를 사용한 **종단 간 실측 테스트**는 별도로 필요합니다.
- 모델 위험 **백분위 점수**를 그대로 A* 회피 비용에 쓰는 현재 방식은 임시 설계입니다. 0–10m/10–15m/15–21m 거리 감쇠, 근거와 평가 방법을 정의한 후 보정해야 합니다.
- B2G DBSCAN 흡연부스 후보는 별도 결과 파일과 API/화면 연결이 필요합니다.

현재 구조는 모델 연결 준비 및 오류 검증 단계이며, **실제 노출 위험도 보정 완료를 의미하지 않습니다.**
