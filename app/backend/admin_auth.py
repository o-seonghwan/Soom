"""Owner and approved administrator authentication via HTTPS HTTP Basic.

The existing ADMIN_USERNAME / ADMIN_PASSWORD are the owner's credentials.
New accounts may log in only after owner approval in PostgreSQL.
"""
import os
import secrets
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from admin_accounts import authenticate_approved, rate_limit

load_dotenv(Path(__file__).resolve().parent / ".env")
security = HTTPBasic(auto_error=False)


def owner_valid(username: str, password: str) -> bool:
    expected_username = os.getenv("ADMIN_USERNAME", "").strip()
    expected_password = os.getenv("ADMIN_PASSWORD", "")
    if not expected_username or not expected_password or expected_password == "CHANGE_ME":
        return False
    return (
        secrets.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8"))
        and secrets.compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
    )


def require_admin(credentials: HTTPBasicCredentials | None = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")
    # Limit verification attempts without storing client IP addresses.
    rate_limit("admin-login:" + credentials.username.casefold(), 30, 60)
    if owner_valid(credentials.username, credentials.password):
        return credentials.username
    try:
        if authenticate_approved(credentials.username, credentials.password):
            return credentials.username
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="관리자 인증 DB 연결에 실패했습니다.") from error
    raise HTTPException(status_code=401, detail="아이디·비밀번호가 틀렸거나 아직 승인되지 않은 계정입니다.")


def require_owner(credentials: HTTPBasicCredentials | None = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="제작자 로그인이 필요합니다.")
    rate_limit("owner-login", 30, 60)
    if not owner_valid(credentials.username, credentials.password):
        raise HTTPException(status_code=403, detail="제작자 전용 기능입니다.")
    return credentials.username


def owner_role(username: str) -> str:
    return "owner" if username == os.getenv("ADMIN_USERNAME", "").strip() else "admin"
