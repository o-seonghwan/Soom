# B2G DBSCAN 흡연시설 입지 후보 — 1차 연동

## 무엇을 보여주는가
- B2G 지도 좌측 상단의 **DBSCAN 입지 추천** 버튼 → 독립 패널 열기
- **주황색 점선 원**: 담배꽁초 적발 기록을 DBSCAN으로 군집화한 집중지의 중심 (설치 좌표 아님)
- **민트색 원**: 입지 분석에서 검토 대상으로 선정한 실제 후보 보행 노드
- 군집별 적발 건수, 판정, 후보 순위, 200m 이내 보행 접근거리, 권장 시설 형태, OOF 위험 확률과 보행 흐름 백분위 표시
- 후보 목록의 **지도에서 보기** → 지도 이동
- 군집 필터, 패널 닫기, 실패 시 다시 불러오기

**입지 후보는 현장 검토 전 분석 결과이며, 실제 설치 가능·허가·흡연 가능 지역을 의미하지 않습니다.**

## 근거 알고리즘 / 입출력

기존 분석 코드:
`notebooks/03_modeling/1_모델학습/4_B2G_흡연구역_입지후보.py`

분석 코드의 기준을 변경하지 않고 결과 파일을 읽습니다.
- DBSCAN: `eps=30m`, `min_samples=30`, 적발 건수 sample weight
- 집중지에서 보행 경로 200m 이내의 후보 탐색
- 법적·민감시설 제한과 보행 노출 흐름 근사치를 기준으로 제외/우선순위 결정
- 군집당 후보 최대 3곳, 입지 형태 제안

분석 코드를 로컬에서 별도로 실행해 실제 CSV를 생성하세요.

```powershell
cd "C:\Users\asia\Desktop\semi 1\do_not_lung\Projects\do_not_lung"
python "notebooks/03_modeling/1_모델학습/4_B2G_흡연구역_입지후보.py"
```

**사전 자료:** 이 모델링 스크립트는 학습용 노드/보행링크, 강남 꽁초 적발 좌표·적발 기록, 공간 5-Fold 분할, 금연구역 및 어린이집 CSV와 파이썬 패키지(scipy, sklearn, xgboost 등)가 필요합니다. 각각 없으면 해당 스크립트의 데이터 준비 단계를 먼저 완료해야 합니다.

기본 출력 디렉터리:
`notebooks/03_modeling/결과/4_입지후보/`

필수 결과 CSV:
- `4_입지후보_군집.csv`
- `4_입지후보_후보지.csv`

`4_입지후보_제외사유.csv`는 분석 참고자료로 저장하지만 이번 지도 API에는 표시하지 않습니다.

## API 연결 방법

분석 결과가 기본 경로에 있다면 별도 설정이 필요 없습니다.

다른 폴더에 결과가 있다면 **백엔드를 실행하는 동일한 PowerShell**에서:

```powershell
$env:LUNG_DBSCAN_RESULTS_DIR = "C:\path\to\4_입지후보"
cd app/backend
python -m uvicorn main:app --reload
```

응답 확인:

```powershell
Invoke-RestMethod http://localhost:8000/api/b2g/dbscan/sites
```

성공 시 `source: dbscan-analysis-csv`, `clusters`, `candidates`, `summary` 반환.
CSV를 찾지 못하거나 컬럼/좌표가 잘못되면 **503 + detail**, 프론트엔드는 경고를 표시하고 임의 후보를 만들지 않습니다.

프론트엔드:

```powershell
cd app/frontend
npm run dev
```

B2G → 지도 위 **DBSCAN 입지 추천** 버튼.

## 안전·데이터 해석

- 꽁초 적발 밀집지역은 흡연 발생의 **대리 지표**입니다. 실제 시설 운영 가능성을 입증하지 않습니다.
- 거리 제한과 제외 조건은 코드에 구현된 잠정 판정이며 **최신 법령/조례와 현장 실사를 대체하지 않습니다.**
- 21m 노출 반경과 통행 대리값(5,000 OD × 난수 시드 3개)은 **설계·모델링 가정**입니다.
- 노출 변화율은 실제 설치 전후 측정치가 아닌 모의 계산 결과입니다.
- 후보 지점은 실제 금연구역인지, 보도 폭·건물 출입구·토지 소유권과 민원이 있는지 검증 후 판단해야 합니다.
- 공개 사용자 지도(B2C) 및 이미 표시되는 실제 흡연구역 CSV는 변경하지 않습니다.
- DBSCAN 군집 중심과 후보 보행 노드는 서로 다르므로 지도에서 두 레이어를 구분합니다.

## 테스트

```powershell
cd app/backend
python -m unittest test_dbscan_sites -v
```

프론트엔드 빌드: `cd app/frontend; npm run build`.
GitHub에는 실제 분석 결과 CSV를 추가하지 않았으며, 테스트는 임시 생성 CSV로 검증합니다.
