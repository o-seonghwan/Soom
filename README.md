# 프로젝트명
폐(Lung) 끼치지 마세요

## 1. 프로젝트 소개
시공간 빅데이터 기반 간접흡연 회피 경로 및 보건행정 솔루션

## 2. 기술 스택
- Python
- Pandas / NumPy
- Scikit-learn
- Git / GitHub

## 3. 폴더 구조(예시)
```text
team-project/
│
├── README.md                   # 프로젝트 소개 및 실행 방법
├── .gitignore                  # 업로드 제외 규칙
├── requirements.txt            # Python 패키지 목록
├── .env.example                # 환경변수 예시(실제 비밀키 제외)
│
├── docs/                       # 기획 및 데이터 문서
│   ├── project_plan.md         # 프로젝트 기획서
│   ├── data_catalog.csv        # 데이터 목록/출처/버전
│   └── data_dictionary.md      # 컬럼 설명
│
├── data/                       # 팀원 PC에서 사용하는 데이터 위치
│   ├── raw/                    # Drive에서 받은 원본(깃 업로드 금지)
│   ├── processed/              # 전처리 결과(깃 업로드 금지)
│   └── sample/                 # 작은 샘플(민감정보 없는 경우만 공유)
│
├── notebooks/                  # 실험용 Jupyter Notebook
│   ├── 01_eda/
│   ├── 02_preprocessing/
│   └── 03_modeling/
│
├── src/                        # 재사용 가능한 Python 코드
│   ├── data/                   # 데이터 로딩/전처리 함수
│   ├── features/               # 피처 엔지니어링
│   ├── models/                 # 모델 학습/평가 코드
│   └── utils/                  # 공통 유틸리티
│
├── scripts/                    # 데이터 처리/학습 실행 스크립트
├── configs/                    # 경로 및 실험 설정
├── tests/                      # 테스트 코드
│
└── reports/
    └── figures/               # 코드로 생성한 작은 분석 그래프
```


## 4. 협업 규칙
- 작업 시작 전 최신 main 확인
- 기능별 브랜치 생성
- 작업 완료 후 Pull Request 생성
- 코드 검토 후 main에 병합

## 5. 강남구 모델 실행

- 원본은 `data/raw/`, 압축을 푼 EDA 결과는 `data/processed/전처리결과/`에 둡니다. 다른 위치는 `LUNG_DATA_ROOT`와 `LUNG_EDA_ROOT`로 지정할 수 있습니다.
- 결과는 `data/processed/결과/`에 저장합니다. 기존 결과 폴더를 연결하려면 `LUNG_OUT_DIR`를 지정합니다.
- 주소별 좌표표가 없다면 `notebooks/02_preprocessing/0_VWorld_좌표찾기.py`를 먼저 실행합니다. VWorld를 쓰려면 저장소 루트의 로컬 `.env`에 `VWORLD_API_KEY`를 설정합니다.

저장소 루트에서 실행합니다.

```powershell
python -m pip install -r requirements.txt
python "notebooks/02_preprocessing/0_머신러닝_전처리.py"
python "notebooks/03_modeling/1_B2C_비흡연자_간접흡연위험지도.py"
```

2·3번은 1번이 만든 위험지도 점수를 읽습니다. 4번은 같은 전처리 입력으로 DBSCAN과 부스 후보 분석을 실행합니다.
