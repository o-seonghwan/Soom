
import os
import secrets

from pathlib import Path

from dotenv import load_dotenv

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
)


# =========================================
# 1. 환경변수 로드
# =========================================

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

security = HTTPBasic(auto_error=False)


# =========================================
# 2. 관리자 인증
# =========================================

def require_admin(
    credentials: HTTPBasicCredentials | None = Depends(
        security
    ),
):
    """
    HTTP Basic 인증으로 관리자 계정 확인.
    아이디와 비밀번호는 .env에서 읽는다.
    """

    expected_username = os.getenv("ADMIN_USERNAME", "")
    expected_password = os.getenv("ADMIN_PASSWORD", "")

    # 관리자 설정이 없는 경우
    if (
        not expected_username
        or not expected_password
        or expected_password == "CHANGE_ME"
    ):
        raise HTTPException(
            status_code=503,
            detail="관리자 계정이 설정되지 않았습니다.",
        )

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="관리자 로그인이 필요합니다.",
        )

    # 문자열 비교 시간을 일정하게 유지
    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        expected_username.encode("utf-8"),
    )

    password_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        expected_password.encode("utf-8"),
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="관리자 아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    return credentials.username
