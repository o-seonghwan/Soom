"""Administrator session cookies for B2G.

The browser never persists the administrator password. Cookie tokens are signed
with a server-only secret and HttpOnly. Rotate ADMIN_SESSION_SECRET to revoke
all outstanding tokens; logout additionally revokes its current nonce.
Deploy behind HTTPS using the same public site for frontend/API.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv(Path(__file__).resolve().parent / ".env")
security = HTTPBasic(auto_error=False)
COOKIE_NAME = "lung_admin_session"
SESSION_SECONDS = 12 * 60 * 60
REMEMBER_SECONDS = 7 * 24 * 60 * 60
# Stateless signed sessions allow multiple API workers to verify the token.
# Logged-out nonce IDs are kept until expiry in each process; a shared session
# revocation store is required when deploying multiple worker instances.
_revoked: dict[str, int] = {}


def _admin_credentials():
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not username or not password or password == "CHANGE_ME":
        raise HTTPException(status_code=503, detail="관리자 계정이 설정되지 않았습니다.")
    return username, password


def _secret() -> bytes:
    secret = os.getenv("ADMIN_SESSION_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(status_code=503, detail="ADMIN_SESSION_SECRET을 32자 이상으로 설정하세요.")
    return secret.encode("utf-8")


def check_password(username: str, password: str) -> str:
    expected_user, expected_password = _admin_credentials()
    if not (secrets.compare_digest(username.encode(), expected_user.encode()) and
            secrets.compare_digest(password.encode(), expected_password.encode())):
        raise HTTPException(status_code=401, detail="관리자 아이디 또는 비밀번호가 올바르지 않습니다.")
    return expected_user


def _encode(data: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _decode(token: str) -> dict:
    try:
        payload, sig = token.split(".", 1)
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("invalid signature")
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        data = json.loads(raw)
        expiry = data["exp"]
        if not isinstance(expiry, int) or expiry <= int(time.time()):
            raise ValueError("expired")
        username, password = _admin_credentials()
        if data.get("user") != username or data.get("pwd") != hashlib.sha256(password.encode()).hexdigest():
            raise ValueError("account changed")
        nonce = data.get("nonce")
        if not isinstance(nonce, str) or not nonce or nonce in _revoked:
            raise ValueError("revoked")
        if not isinstance(data.get("csrf"), str):
            raise ValueError("invalid csrf")
        return data
    except (ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=401, detail="관리자 세션이 만료되었거나 유효하지 않습니다.") from error


def create_session(username: str, remember: bool) -> tuple[str, dict]:
    _, password = _admin_credentials()
    expiry = int(time.time()) + (REMEMBER_SECONDS if remember else SESSION_SECONDS)
    data = {
        "user": username,
        "exp": expiry,
        "nonce": secrets.token_urlsafe(24),
        "csrf": secrets.token_urlsafe(24),
        "pwd": hashlib.sha256(password.encode()).hexdigest(),
    }
    return _encode(data), {"authenticated": True, "username": username, "csrfToken": data["csrf"], "expiresAt": expiry}


def get_cookie_session(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")
    return _decode(token)


def revoke_session(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return
    data = _decode(token)
    # Expired nonce entries are removed on every logout.
    now = int(time.time())
    for nonce, expiry in list(_revoked.items()):
        if expiry <= now:
            del _revoked[nonce]
    _revoked[data["nonce"]] = data["exp"]


def require_admin(request: Request, credentials: HTTPBasicCredentials | None = Depends(security)):
    if credentials is not None:
        return check_password(credentials.username, credentials.password)
    data = get_cookie_session(request)
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        supplied = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(supplied, data["csrf"]):
            raise HTTPException(status_code=403, detail="관리자 요청의 보안 토큰이 없습니다.")
    return data["user"]
