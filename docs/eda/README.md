# 팀원별 데이터셋 EDA 작업 안내

대상 프로젝트: 폐(Lung) 끼치지 마세요 — 시공간 데이터 기반 간접흡연 회피 도보 경로 서비스

## 1. 목적과 결과물
팀원마다 한 데이터셋을 맡아 재실행 가능한 Jupyter Notebook을 작성하고, 정제 CSV / 요약 CSV / 가능하면 파생변수 CSV를 생성한다.

- Notebook: notebooks/01_eda/EDA_데이터셋명.ipynb (GitHub 버전 관리)
- 정제본: data/processed/데이터셋명_clean.csv (로컬·Drive 공유)
- EDA 수치 요약: data/processed/데이터셋명_summary.csv (로컬·Drive 공유)
- 파생변수: data/processed/데이터셋명_features.csv (생성 가능한 경우)
- 주요 발견 및 적용 판단: docs/eda/에 Markdown 문서로 공유 권장

**중요**: 현재 .gitignore는 data/raw/와 data/processed/를 제외하므로 CSV는 자동으로 Git에 올라가지 않는다. 이전에 이미 Git에 추적된 raw 파일은 이 규칙을 새로 적용해도 사라지지 않는다. 큰 CSV를 강제 추가하지 말 것.

## 2. 시작하기 (Windows PowerShell, 저장소 루트)
1. GitHub 저장소를 clone 또는 pull한다.
2. Python 3.11 또는 3.12를 사용한다.
3. 아래처럼 EDA 전용 가상환경을 설치한다.

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-eda.txt
python -m ipykernel install --user --name do-not-lung-eda --display-name "Python (do-not-lung-eda)"
~~~

VS Code의 Python, Jupyter 확장을 설치하고 Notebook 커널을 선택한다. py -3.12가 없는 경우 설치된 3.11/3.12 경로로 변경한다.

## 3. 데이터 위치
- 받은 원본 파일은 data/raw/ 아래에 보관한다.
- GitHub에 기존 데이터 파일이 일부 이미 추적되어 있지만, 그 사실을 근거로 새 대용량 원본까지 commit하지 않는다.
- 누락된 대용량 도보 네트워크 CSV와 상권정보 ZIP은 Drive에 업로드·공유한 뒤 담당자가 내려받아 data/raw/에 배치한다.
- 데이터셋 원본 파일명, 기준일, 출처, 경로, 단위, 예상 용량을 Notebook 맨 앞에 기재한다.
- CSV 결과 파일은 data/processed/에 자동 저장하되 GitHub PR에는 Notebook과 요약 문서만 제출한다.

## 4. 공통 Notebook 목차
1. 데이터 설명 및 수집 기준일
2. 로드 및 컬럼 사전 (자료형, 샘플, 식별자)
3. 결측·중복·이상치 검증
4. 기초 통계와 그래프 및 결과 해석
5. 위치·시간 해상도와 좌표계 검증
6. 정제 과정과 전후 비교
7. 요약 CSV와 clean CSV 저장, 재읽기 검증
8. 파생변수 생성 가능성 (생성했다면 features CSV)
9. 프로젝트 적용: 250m 격자·위험요인 분석·ML·경로 가중치 중 실제 가능한 부분
10. 한계, 추가 데이터, 최종 활용 판단

## 5. 팀 내 공통 규칙
- **공간**: 250m 격자 기준 및 투영 좌표계는 팀 전체 협의 후 공통 정의한다. 독자적인 grid_id는 생성하지 않는다. 거리·면적 연산에는 위경도(degree)가 아닌 미터 단위 투영 좌표를 사용한다.
- **시간**: 관측 날짜·시간대와 데이터 기준일을 구분한다.
- **라벨**: 흡연시설/금연구역/생활인구는 흡연 발생 정답 라벨이 아니다. 임의 라벨을 만들어 지도학습 성능을 주장하지 않는다.
- **전처리**: 원본 불변, 전후 행 수, 누락과 제외 근거를 문서화한다.
- **CSV**: UTF-8-SIG 저장, index=False, 컬럼명·단위 기록, 저장 후 재검증한다.
- **대용량**: 메모리 부족이면 청크 처리·필요 컬럼 로드·Parquet 중간 변환을 사용하되 원본 변경은 금지한다.

## 6. GitHub 협업
- main에서 최신 pull 후 데이터셋별 브랜치를 만든다 (예: eda/bus-stops).
- notebooks/01_eda/EDA_TEMPLATE.ipynb를 복제해 분석한다.
- Notebook과 소형 요약 문서만 commit한다.
- PR에는 분석 대상, 주요 발견, 생성한 로컬/Drive CSV 경로, 사용 변수, 제약, 재현 방법을 기재한다.
- docs/eda/DATA_INVENTORY.md의 저장소 데이터 현황과 빠진 파일을 확인한다.

## 7. 분석 도구
pandas/NumPy: 데이터 품질·집계; matplotlib/seaborn: 그래프; GeoPandas/Shapely/pyproj: 공간 연산; scikit-learn: 적합한 목표/라벨이 있는 경우 모델링; networkx: 노드·링크 연결 및 최단 경로. 불필요한 라이브러리까지 강제로 사용하지 않는다.
