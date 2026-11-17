# 강남구 흡연구역 데이터 → 지도 연결

이 작업은 **`강남구_흡연구역.xlsx`**만 사용합니다. 강남구 흡연단속내역, 담배꽁초, 금연구역은 흡연시설로 취급하거나 지도 흡연구역 레이어에 연결하지 않습니다.

## 데이터 상태

- 저장소 전처리 코드: `notebooks/02_preprocessing/0_강남구_흡연구역_전처리.py` (원본의 주소·좌표·비고·출처 필요)
- Drive 원본 `강남구_흡연구역.xlsx`: 현재 연결 계정의 검색 결과에서 확인되지 않음
- 앱 연결: 환경변수 `LUNG_SMOKING_ZONES_CSV`가 지정된 경우에만 CSV 로딩
- CSV가 없으면 기존처럼 `source=not-configured`, `zones=[]` 반환

## 1. 원본 확보 및 전처리

원본 파일의 실체와 정확한 스키마를 확인한 다음 아래 명령을 실행합니다.
VWorld 키는 로컬 환경변수에만 두고 커밋하지 마세요.

```powershell
$env:VWORLD_API_KEY = "발급받은_키"
python "notebooks/02_preprocessing/0_강남구_흡연구역_전처리.py" "C:\\datasets\\강남구_흡연구역.xlsx" --output "C:\\datasets\\강남구_흡연구역_전처리.xlsx"
```

주소→좌표 변환 결과는 **주소 기반 추정값**일 수 있으며 실제 흡연부스 위치를 보증하지 않습니다.

## 2. 앱용 CSV 내보내기

전처리 결과에 `위치검증` (또는 `좌표검증`, `위치검증상태`) 열이 있고 `검증완료` / `현장확인` 등으로 확인된 행만 기본적으로 내보냅니다.

```powershell
python "notebooks/02_preprocessing/1_강남구_흡연구역_앱연결.py" "C:\\datasets\\강남구_흡연구역_전처리.xlsx" --output "C:\\datasets\\gangnam_smoking_zones.csv"
```

전처리 엑셀에 현장 검증 열이 없거나 검증된 행이 없으면 기본 모드에서는 CSV를 생성하지 않습니다. **주소 기반 추정 위치도 지도에 표시하기로 명시적으로 판단한 경우에만** 아래 옵션을 사용합니다.

```powershell
python "notebooks/02_preprocessing/1_강남구_흡연구역_앱연결.py" "C:\\datasets\\강남구_흡연구역_전처리.xlsx" --output "C:\\datasets\\gangnam_smoking_zones.csv" --include-address-level
```

이 경우 API와 지도 팝업에 `address-level`이 표시되어 실측 부스 위치와 구분됩니다. 좌표가 없는 행, 범위 밖 좌표, 비정상 데이터는 제외됩니다.

## 3. FastAPI 연결

```powershell
$env:LUNG_SMOKING_ZONES_CSV = "C:\\datasets\\gangnam_smoking_zones.csv"
cd app/backend
python -m uvicorn main:app --reload
```

`http://localhost:8000/api/smoking-zones` 응답을 확인하세요. `source= configured-csv`와 `zones` 목록이 나오면 B2C/B2G 지도 오른쪽 위의 🚬 버튼을 눌러 마커를 표시할 수 있습니다.

## 검증

```powershell
python -m unittest discover -s app/backend -p "test_gangnam_smoking_export.py" -v
python -m unittest discover -s app/backend -p "test_smoking_zones.py" -v
```

데이터 원본 미확보 상태에서는 실제 흡연시설 개수, 좌표 정확도, 지도 표시 품질을 확정할 수 없습니다. 기본 API는 좌표를 임의 생성하지 않습니다.
