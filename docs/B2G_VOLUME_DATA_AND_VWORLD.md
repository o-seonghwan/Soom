# B2G 실제 분석 CSV를 Railway Volume에 연결하기

이 문서는 없는 모델 결과나 시설 좌표를 생성하지 않습니다.

## 현재 실패 원인

`soom-backend` Dockerfile은 `app/backend`만 복사합니다. 따라서 `notebooks/03_modeling/결과/`의 오프라인 생성 파일은 운영 컨테이너에 없으며 B2G API는 HTTP 503을 반환합니다.

## 필요한 세 파일

| API | 실제 분석 출력 파일 |
| --- | --- |
| `GET /api/b2g/childcare/exposure` | `3_어린이집_노출순위.csv` |
| `GET /api/b2g/dbscan/sites` | `4_입지후보_군집.csv`, `4_입지후보_후보지.csv` |

모델 생성 원본:
- `notebooks/03_modeling/2_서비스/3_B2G_비흡연자_아동간접흡연보호리포트.py`
- `notebooks/03_modeling/1_모델학습/4_B2G_흡연구역_입지후보.py`

CSV가 없다면 먼저 관련 데이터 준비 및 위 모델 코드 실행이 필요합니다. 임의의 후보지 CSV는 올리지 마세요.

## Windows PowerShell에서 업로드

Railway CLI 로그인 및 `Soom` 프로젝트/`soom-backend` 서비스 연결 후:

```powershell
railway status

railway volume files upload "C:\\실제파일경로\\3_어린이집_노출순위.csv" "/3_어린이집_노출순위.csv"
railway volume files upload "C:\\실제파일경로\\4_입지후보_군집.csv" "/4_입지후보_군집.csv"
railway volume files upload "C:\\실제파일경로\\4_입지후보_후보지.csv" "/4_입지후보_후보지.csv"
```

배포된 `soom-backend`의 볼륨 마운트는 `/app/data/processed/walking_network`입니다. 세 파일은 이 디렉터리에 위치합니다. 볼륨 루트에 업로드하는 CLI 명령의 두 번째 인자는 `/파일명`입니다.

새 로더는 환경변수가 별도 지정되지 않은 경우 `RAILWAY_VOLUME_MOUNT_PATH`의 실제 CSV 파일을 읽습니다. 별도의 `LUNG_CHILDCARE_EXPOSURE_CSV` 또는 `LUNG_DBSCAN_RESULTS_DIR` 지정은 필수가 아닙니다. 기존에 경로 환경변수가 지정돼 있다면 그 경로가 우선합니다.

### 확인

제작자 또는 승인된 관리자로 로그인한 뒤
- 어린이집 보호 우선순위
- DBSCAN 입지 추천
탭에서 **새로고침**을 실행하세요.

서버 오류가 지속된다면 정확한 CSV 컬럼명, 좌표와 값 범위가 `childcare_exposure.py`, `dbscan_sites.py`의 검증과 맞는지 확인합니다.

## VWorld 검색 연결

`soom-backend`의 `VWORLD_API_KEY`는 이미 등록됐지만 실제 API가 HTTP 503으로 응답합니다. 인증키 발급 페이지에 등록한 도메인이 제한된 키라면 같은 서비스에

`VWORLD_DOMAIN=https://soom-production-be127e6c.up.railway.app`

을 등록하되, **이 URL이 실제 VWorld 키에 등록된 도메인인 경우에만** 사용하세요. 백엔드는 선택적 `domain` 파라미터와 `Referer`를 전송하고 안전한 인증 오류 메시지를 반환합니다. 키 문자열은 GitHub에 올리지 마세요.
