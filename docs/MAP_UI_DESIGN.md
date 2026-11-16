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
