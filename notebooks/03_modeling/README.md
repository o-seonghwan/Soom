# 03_modeling · 머신러닝 코드

`공통.py`는 이 폴더 바로 아래에 두고, 나머지 코드는 용도별 하위 폴더에 있습니다. 하위 폴더의 코드는 `공통.py`를 자동으로 찾아 불러옵니다.

| 폴더 | 내용 |
|---|---|
| `공통.py` | 모든 코드가 불러 쓰는 데이터 읽기·특성 계산 모듈 |
| `1_모델학습/` | 전처리(학습표 12,052행 × 27열), 공간 5-Fold 분할, **지도학습** XGBoost 위험 모델(`1_B2C_비흡연자_간접흡연위험지도.py`), **비지도학습** DBSCAN 흡연구역·부스 입지 후보(`4_B2G_흡연구역_입지후보.py`) |
| `2_서비스/` | B2C 흡연 가능 판정, B2G 아동 간접흡연 보호 리포트 (1번 위험지도 결과를 읽음) |
| `3_선택/` | VWorld 좌표 찾기, 마포 외부검증, 위험지도+마포검증 묶음 실행 |
| `4_실험/` | XGBoost·LightGBM 튜닝, 개선 실험(SMOTENC, F2 임계값, 판정 기준, 생활인구 격자), 예전 DBSCAN 부스 후보, DBSCAN 설정 비교 |

## 실행 순서
```
python 1_모델학습/0_머신러닝_전처리.py
python 1_모델학습/0_공간5Fold_분할.py
python 1_모델학습/1_B2C_비흡연자_간접흡연위험지도.py
python 1_모델학습/4_B2G_흡연구역_입지후보.py
python 2_서비스/2_B2C_흡연자_여기서피워도되나요.py
python 2_서비스/3_B2G_비흡연자_아동간접흡연보호리포트.py
```
결과는 어느 폴더에서 실행해도 `03_modeling/결과/`에 저장됩니다. 이 폴더는 깃허브에 올리지 않습니다(.gitignore).

## 데이터 위치
코드가 아래 순서로 데이터를 찾습니다.
1. 환경변수 `LUNG_DATA_ROOT`(원본), `LUNG_EDA_ROOT`(전처리본)
2. 환경변수 `LUNG_DRIVE_ROOT` 아래의 `processed_data/`·`raw_data/` 또는 `data/processed/`·`data/raw/`
3. 기존 PC 구조 (`02_1_분석데이터/`, `전처리결과/`)
4. 이 폴더와 상위 세 단계에서 자동 탐색: 저장소의 `data/processed/`·`data/raw/` 또는 드라이브 구조 `processed_data/`·`raw_data/`

저장소 구조라면 `data/processed/`에 전처리본(생활인구 `local_resd_250m*`, 도보 네트워크, 강남구 꽁초 적발, 마포구 꽁초), `data/raw/` 아래 어디든 원본(상가, 버스정류소, 금연구역, 어린이집, 건물 `AL_D010*.zip`, 천식, 흡연단속)이 있으면 됩니다. 데이터 폴더는 .gitignore 대상이라 팀 드라이브에서 받아 넣어 주세요.

## 실행 전에 필요한 파일 (깃허브에 없음)
`결과/` 폴더에 아래 세 파일이 있어야 합니다. VWorld 조회 결과라 약관상 저장소에 올리지 않습니다.
- `결과/정답_꽁초적발_장소좌표.csv`
- `결과/vworld_캐시_꽁초.csv`
- `결과/강남_꽁초적발_전체기록_좌표.csv`

팀 공유 폴더에서 받거나, `.env`에 `VWORLD_API_KEY`를 넣고 `python 3_선택/0_VWorld_좌표찾기.py`로 다시 만듭니다. `.env`도 올리지 마세요.

## 필요한 패키지
pandas, numpy, scikit-learn, scipy, geopandas, shapely, pyogrio, networkx, openpyxl, requests, xgboost, lightgbm, joblib
