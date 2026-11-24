"""PostgreSQL-backed, owner-approved B2G administrator accounts.

The Railway ADMIN_USERNAME / ADMIN_PASSWORD pair remains the sole owner.
Requested accounts have no rights until the owner approves them.
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

import psycopg
from fastapi import HTTPException

from db import get_connection

USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{3,39}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SALT_BYTES = 16
HASH_ITERATIONS = 350_000

# A basic per-process anti-abuse limit. Production edge-level limits should
# additionally be configured on the public proxy before large-scale rollout.
_attempts = defaultdict(deque)
_attempt_lock = Lock()


def rate_limit(key: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    with _attempt_lock:
        entries = _attempts[key]
        while entries and now - entries[0] >= window_seconds:
            entries.popleft()
        if len(entries) >= limit:
            raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 잠시 뒤 다시 시도하세요.")
        entries.append(now)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256:{HASH_ITERATIONS}:{base64.b64encode(salt).decode()}:{base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, encoded_salt, encoded_digest = stored.split(":")
        if algo != "pbkdf2_sha256" or int(rounds) < 200_000:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
            base64.b64decode(encoded_salt), int(rounds))
        return hmac.compare_digest(digest, base64.b64decode(encoded_digest))
    except (ValueError, TypeError):
        return False


def apply_for_admin(username: str, password: str, email: str,
                    organization: str, reason: str) -> dict:
    username, email, organization, reason = (
        username.strip(), email.strip().lower(), organization.strip(), reason.strip())
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(status_code=422, detail="아이디는 영문자로 시작하는 영문·숫자·._- 4~40자여야 합니다.")
    if not EMAIL_PATTERN.fullmatch(email) or len(email) > 254:
        raise HTTPException(status_code=422, detail="올바른 이메일을 입력하세요.")
    if len(password) < 12 or len(password) > 128 or len(password.encode("utf-8")) > 512:
        raise HTTPException(status_code=422, detail="비밀번호는 12~128자로 입력하세요.")
    if not (2 <= len(organization) <= 160 and 10 <= len(reason) <= 800):
        raise HTTPException(status_code=422, detail="소속 2~160자 및 신청 사유 10~800자를 입력하세요.")
    if username.casefold() == os.getenv("ADMIN_USERNAME", "").casefold():
        raise HTTPException(status_code=409, detail="사용할 수 없는 아이디입니다.")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO admin_users
                       (username, email, organization, reason, password_hash)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING id""",
                    (username, email, organization, reason, hash_password(password)),
                )
                account_id = cur.fetchone()[0]
        return {"requestId": str(account_id), "status": "pending",
                "message": "계정 신청을 접수했습니다. 제작자가 승인하기 전에는 로그인할 수 없습니다."}
    except psycopg.errors.UniqueViolation as error:
        raise HTTPException(status_code=409, detail="이미 신청된 아이디입니다.") from error


def authenticate_approved(username: str, password: str) -> bool:
    # Reject empty credentials and avoid querying if no username.
    if not username or not password:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash, status FROM admin_users WHERE username = %s", (username,))
            row = cur.fetchone()
    return bool(row and row[1] == "approved" and verify_password(password, row[0]))


def list_applications() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, username, email, organization, reason, status,
                          requested_at, reviewed_at, reviewed_by, review_note
                   FROM admin_users
                   ORDER BY CASE WHEN status='pending' THEN 0 ELSE 1 END,
                            requested_at DESC LIMIT 250"""
            )
            rows = cur.fetchall()
    return [
        {"id": str(row[0]), "username": row[1], "email": row[2],
         "organization": row[3], "reason": row[4], "status": row[5],
         "requestedAt": row[6].isoformat(), "reviewedAt": row[7].isoformat() if row[7] else None,
         "reviewedBy": row[8], "reviewNote": row[9]}
        for row in rows
    ]


def review_application(account_id: str, decision: str, actor: str,
                       review_note: str = "") -> dict:
    if decision not in ("approved", "rejected", "disabled"):
        raise HTTPException(status_code=422, detail="승인, 반려 또는 비활성화만 가능합니다.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE admin_users
                   SET status=%s, reviewed_at=now(), reviewed_by=%s, review_note=%s
                   WHERE id=%s::uuid AND status IN ('pending', 'approved')
                   RETURNING username, status""",
                (decision, actor, review_note[:800], account_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="변경 가능한 신청을 찾지 못했습니다.")
            cur.execute(
                """INSERT INTO admin_audit_logs(actor, action, target_username, detail)
                   VALUES (%s, %s, %s, %s)""",
                (actor, decision, row[0], review_note[:800]),
            )
    return {"username": row[0], "status": row[1]}
