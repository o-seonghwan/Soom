# B2G 관리자 로그인 유지 기능

## 동작

- 로그인 체크박스 **로그인 유지 (최대 7일)**: 미선택 시 브라우저 세션 쿠키(서버 만료 12시간), 선택 시 7일 쿠키
- 관리자 아이디/비밀번호는 로그인 요청에만 전송하며 브라우저 localStorage/sessionStorage에 저장하지 않음
- `HttpOnly`, `SameSite=Lax` 관리자 인증 쿠키 + 서버 비밀키를 사용하는 서명/만료 검증
- 관리자 페이지로 돌아오거나 새로고침하면 `GET /api/admin/me`로 세션 검증 후 제보 목록 복원
- 로그아웃은 `DELETE /api/admin/session`으로 세션 무효화 및 쿠키 삭제
- 제보 승인·반려(PATCH)는 브라우저 쿠키뿐 아니라 `X-CSRF-Token`도 요구
- DBSCAN/어린이집 관리자 API는 동일 세션 쿠키로 인증

## 백엔드 환경변수

`app/backend/.env` (개인 키를 Git에 커밋하지 말 것):

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD=강력한_고유_관리자_비밀번호
ADMIN_SESSION_SECRET=32자_이상의_별도_무작위_비밀키
ADMIN_COOKIE_SECURE=false
```

비밀키 생성:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

운영 HTTPS 환경에는 반드시 `ADMIN_COOKIE_SECURE=true` 설정. 프론트엔드와 /api를 **같은 HTTPS 사이트**로 reverse proxy 연결하는 방식 권장. 다른 오리진을 사용하는 경우 `ADMIN_ALLOWED_ORIGINS`와 CORS 설정을 맞춰야 하고, SameSite=Lax 쿠키가 다른 사이트로 전송되지 않을 수 있으므로 동일 사이트 배포 권장.

## 공개 배포 전 보안 제한 사항

- 현재는 프로토타입용 단일 관리자 비밀번호 인증. 공개 배포에는 계정별 권한, 로그인 시도 제한, 비밀번호 저장·변경 정책, 활동 감사 로그 강화가 필요함
- 로그아웃 무효화 목록은 현재 **프로세스 메모리**에 있음. 서버 재시작이나 다중 워커/인스턴스 환경에서 즉시 무효화가 보장되지 않음. **Redis/PostgreSQL 등 공유 세션 저장소에 세션 무효화와 발급 정보를 저장**하는 설계로 변경 후 공개 배포해야 함
- 서버용 서명 비밀키를 변경하면 기존 쿠키 세션이 모두 무효화됨. 세션 토큰이 유출되면 비밀키를 회전하고 사용자 재로그인을 유도할 것
- HTTPS 외 환경에서 운영하면 보안 쿠키 전송 보호가 불가능함. localhost만 개발 예외로 허용
- 브라우저가 닫혀도 세션을 복원하는 기능은 공용 기기에서 위험하므로 사용자가 체크박스를 직접 선택해야 함

## 어린이집 검색 스크롤

어린이집 카드 목록의 스크롤 공간을 `45dvh`로 고정하고 `overflow-anchor: none`을 사용. 검색 결과가 0건이 되어도 카드 영역 높이를 유지해 외부 패널이 갑자기 움직이는 현상을 방지.
