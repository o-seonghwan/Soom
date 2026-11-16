# 지도 디자인 브랜치 (B2C/B2G)

## 브랜치와 변경 범위
- 기준: 기존 `feature/b2g-cleanliness-roads` → PR #10 → `main` 병합 커밋 `40c7dcc5`
- 별도 디자인 브랜치: `feature/map-ui-design`. PR #12에서만 작업, `main`에 디자인 수정 미병합.
- B2C: 최단 경로 `#D8DAD3`, 위험 회피 경로 `#A68A64`
- B2C: 지도 왼쪽 위에 출발지/목적지 카드, 출발/목적지 지도 선택 및 서로 바꾸기
- B2C: 설정/신고 패널을 접고 펼칠 수 있도록 변경해 기본 지도 영역을 넓힘
- B2C: 경로 탐색 성공 후 두 경로 전체 좌표를 포함하도록 Leaflet `fitBounds` 실행
- B2C: 현재 위치는 버튼 누른 뒤 안내창 동의한 경우에만 브라우저 권한 요청. 오른쪽 아래 버튼은 **지도 중심만** 이동, 출발지 자동 변경 없음
- B2C와 B2G: 지도 오른쪽 위 🚬 버튼으로 흡연시설 위치 토글
- 공통: '강남구 서비스 지역' 오른쪽 위 안내 카드만 제거, 강남구 경계 마스크는 유지

## 흡연시설 데이터 연결

**현재 저장소에는 즉시 지도에 띄울 수 있는 검증된 흡연시설 위치 CSV가 없습니다.** 임의 위치 생성이나 금연구역 데이터를 흡연시설로 바꾸는 처리는 하지 않습니다.

실외 공공 흡연시설의 공식 참고 데이터: 서울시 열린데이터광장 '서울시 실외흡연 시설 현황' (2026-09-10 갱신): https://data.seoul.go.kr/dataList/OA-22191/S/1/datasetView.do

CSV를 준비할 때는 실제 시설명·좌표를 검증해 다음 컬럼으로 저장해야 합니다.

```csv
name,lat,lng
```

**위는 헤더만 있는 예제이며 실제 시설 좌표를 포함하지 않습니다.** 공개 데이터에 주소만 있고 위경도가 없다면 신뢰할 수 있는 지오코딩과 장소 검증 과정을 선행해야 합니다.

백엔드 실행 전 같은 PowerShell 터미널에서 설정:

```powershell
$env:LUNG_SMOKING_ZONES_CSV = "C:\\datasets\\verified_smoking_zones.csv"
cd app/backend
python -m uvicorn main:app --reload
```

정상 연결 시 `GET /api/smoking-zones` → `source:configured-csv`와 시설 목록. 미설정이면 `source:not-configured`와 빈 목록을 반환하고, 지도 버튼을 누르면 데이터가 없음을 안내합니다. 잘못된 파일이나 좌표는 HTTP 503 오류로 표시됩니다.

흡연시설 목록은 서울시의 '공공 실외 시설' 범위만 포함하며, 모든 합법적 흡연 가능 위치를 뜻하지 않습니다. 방문 전에 현장 운영상태와 표지를 확인해야 합니다.

## 검증
- `python -m unittest discover -s app/backend -p "test_smoking_zones.py" -v`
- `cd app/frontend; npm run build; npm run lint`
- 실제 브라우저 수동 검증은 아직 필요: 작은 화면에서 경로 카드와 서비스 다시 선택 버튼 겹침, 현재 위치 권한 거절, 출발/목적지 교환, 먼 거리 경로 전체 보기, 흡연 시설 좌표 마커 표시.


## 2026-11-16 후속 UI 개편

- B2C 경로: 최단 `#343A40`, 회피 `#72EFDD` (지도 선과 경로 결과 카드 배경 동일).
- 좌상단 경로 카드에서 **경로 탐색** 가능. 출발지/목적지의 표시명은 역지오코딩 결과 주소.
- 기존 접이식 탭은 **회피 강도 / 최단 경로 / 회피 경로 / 흡연 제보**로 분리.
- 최단/회피 결과에 거리 및 예상 시간을 각각 표시하며, 기존 좌표 직접 입력 기능은 회피 강도/결과 탭 아래 '좌표 직접 입력'으로 유지.
- B2C 청정지수 Canvas: 투명도 누적 방지를 위해 검정 바탕에서 최대 grayscale 합성 후 단일 색상 alpha로 적용. 지도 이동 시작 시 잠시 숨기고 이동 완료 후 재생성(잔상 완화).
- 지도 선 끝·교차점은 round로 처리. **지도 출력의 부드러움은 브라우저·확대 수준에 따라 차이가 있어 수동 테스트가 필요**.

## 주소 API 연결 (Kakao Local)

카카오 Developers에서 앱을 등록하고 **REST API 키**를 발급받아 백엔드 환경변수로 설정합니다. 백엔드 시작 터미널의 PowerShell 예:

```powershell
$env:KAKAO_REST_API_KEY = "카카오_앱의_REST_API_키"
cd app/backend
python -m uvicorn main:app --reload
```

`app/backend/.env.example`은 참고 파일일 뿐 자동으로 환경변수를 설정하지 않습니다. API 키를 프론트엔드의 `VITE_*`나 GitHub에 넣으면 안 됩니다.

카카오 좌표→주소 API는 `GET https://dapi.kakao.com/v2/local/geo/coord2address.json?x={경도}&y={위도}&input_coord=WGS84`입니다. 백엔드 `GET /api/reverse-address?lat=37.5&lng=127.02`가 이 API를 서버에서 호출하고 응답을 캐싱합니다. 키 미설정/검색 실패 시 지도 경로 계산을 중단하지 않고 **좌표와 주소 확인 불가 안내**로 대신 표시합니다.

참고: https://developers.kakao.com/docs/latest/ko/local/dev-guide#coord-to-address

## 흡연구역 지도 API 연결

**이미 연결된 앱 API**는 `GET /api/smoking-zones`입니다. B2C/B2G 우상단 🚬 버튼이 이 URL을 조회합니다. 하지만 실제 위치를 반환하려면 검증된 데이터가 필요합니다.

1. [서울시 실외흡연 시설 현황](https://data.seoul.go.kr/dataList/OA-22191/S/1/datasetView.do)에서 최근 원본 XLSX 또는 CSV를 받습니다.
2. 시트의 시설명·설치위치를 확인합니다. 원본에는 위경도가 없고, 민간이 설치한 흡연시설은 포함하지 않으므로 **지도 마커로 곧바로 변환할 수 없습니다.**
3. 설치 위치를 좌표로 지오코딩한 뒤 실제 시설 위치와 일치하는지 확인합니다. '역 주변', '빌딩 옆'처럼 넓은 표현은 자동 지오코딩의 중심점으로 사용하지 않고 검증하거나 제외합니다.
4. 아래 형태로 검증한 위치를 CSV에 저장합니다.

```csv
name,lat,lng
```

5. 백엔드 실행 터미널에서 설정하고 재시작합니다.

```powershell
$env:LUNG_SMOKING_ZONES_CSV = "C:\\data\\verified_smoking_zones.csv"
cd app/backend
python -m uvicorn main:app --reload
```

6. 새 PowerShell에서 아래처럼 확인합니다.

```powershell
Invoke-RestMethod http://localhost:8000/api/smoking-zones |
    Select-Object source, zones
```

`source: configured-csv`이고 `zones`에 실제 시설이 있을 때 지도에 표시합니다. 미설정이면 `not-configured`와 빈 목록을 반환합니다. **서울시 원본 자료를 온라인에서 직접 주기적으로 가져와서 좌표까지 자동 생성하는 서버는 아직 만들지 않았습니다.** '흡연구역'과 '금연구역'을 혼동하지 않도록 `nosmoking_zones_*.csv`를 이 API에 연결하지 마세요.

원본 자료의 대상은 공공 실외시설이며 현재 운영 중인지와 흡연 가능 범위는 현장 안내가 우선합니다.
