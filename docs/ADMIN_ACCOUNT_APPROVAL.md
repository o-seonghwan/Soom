# B2G 관리자 계정 신청과 제작자 승인

## 현재 브랜치
`feature/b2c-mobile-admin-panel-20261124` — PR #38. `main`/Railway에는 병합 전까지 적용되지 않습니다.

## 역할

- **제작자(owner)**: Railway `soom-backend` 환경변수 `ADMIN_USERNAME`, `ADMIN_PASSWORD`에 등록된 기존 관리자 한 명
- **신청자(pending)**: 관리자 로그인·제보 조회·제보 승인·B2G 보호 데이터 조회가 모두 거부됨
- **승인 관리자(approved)**: B2G 관리자 API 및 제보 검토 사용 가능. 계정 승인/반려는 불가능
- **반려(rejected), 비활성화(disabled)**: 관리자 접근 거부

## 사용 흐름

1. B2G 관리자 로그인 창에서 **새 관리자 계정 신청** 선택
2. 아이디, 12자 이상 비밀번호, 이메일, 소속 및 신청 사유 작성
3. `POST /api/admin/applications` → PostgreSQL `admin_users`에 `pending` 저장 (비밀번호는 솔트 PBKDF2-SHA256 해시만 저장)
4. 제작자 계정으로 B2G 관리자 로그인 후 대시보드의 **관리자 계정 승인 · 제작자 전용** → **신청 목록 조회**
5. 신청 내용 확인 후 승인/반려 (서버에서 제작자 자격증명 검사)
6. 승인된 계정만 기존 로그인 화면에서 로그인 가능. 승인/반려/비활성화 이력은 `admin_audit_logs`에 저장

## 주요 엔드포인트

| Endpoint | 권한 |
|---|---|
| `POST /api/admin/applications` | 공개 신청, 속도 제한 적용 |
| `GET /api/admin/applications` | 제작자만 |
| `PATCH /api/admin/applications/{account_id}` | 제작자만 |
| `GET /api/admin/me` | 제작자/승인 관리자; `role` 반환 |
| 기존 `/api/admin/reports` | 제작자/승인 관리자 |

## 배포 시 주의사항

- 서버 사전 배포 명령 `python app/backend/init_db.py`가 기존 테이블을 유지하면서 `002_admin_accounts.sql`을 실행합니다.
- Railway `soom-backend`의 기존 `ADMIN_USERNAME`/`ADMIN_PASSWORD` 값을 유지하세요. GitHub나 브라우저 빌드 환경변수로 복사하지 마세요.
- 브라우저는 HTTPS를 통해 HTTP Basic 헤더로 로그인하며 서버가 매 요청마다 계정 상태를 확인합니다.
- 이메일 확인·자동 승인 알림은 **미구현**입니다. 제작자가 대시보드에서 직접 새 신청을 조회해야 합니다.
- 퍼블릭 배포 전에는 프록시/방화벽 수준의 IP 제한, 로그인 실패 방어 및 HTTPS 상태를 별도 검토하세요. 코드의 속도 제한은 단일 프로세스 메모리 기반의 기본 방어에 불과합니다.
- 사용자 비밀번호 또는 신청자 개인정보를 로그나 GitHub에 기록하지 마세요.
- 기존 UI 요청에 따라 제거한 로그아웃 버튼은 복구하지 않았습니다. 공유 기기 세션 관리 정책은 별도 검토가 필요합니다.

## 테스트

```powershell
python -m unittest discover -s app/backend -p "test_admin_approval.py" -v
cd app/frontend
npm ci
npm run build
```

전체 `npm run lint`에는 기존 React Hooks 규칙 오류가 남아 있어 별도로 수정해야 합니다.
