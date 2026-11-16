
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# =====================================================
# 1. 환경변수 읽기
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


# =====================================================
# 2. 연결 설정 확인
# =====================================================

def get_db_config():
    """
    .env의 설정을 PostgreSQL 연결 인자로 변환한다.
    """

    password = os.getenv("DB_PASSWORD")

    if not password or password == "YOUR_LOCAL_PASSWORD":
        raise ValueError(
            "app/backend/.env에 실제 "
            "DB_PASSWORD를 설정하세요."
        )

    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv(
            "DB_NAME", "do_not_lung"
        ),
        "user": os.getenv("DB_USER", "lung_app"),
        "password": password,
        "connect_timeout": 5,
    }


# =====================================================
# 3. PostgreSQL 연결
# =====================================================

def get_connection():
    """
    호출할 때 새로운 DB 연결을 반환한다.

    사용 예:
        with get_connection() as conn:
            ...
    """

    return psycopg.connect(**get_db_config())


# =====================================================
# 4. DB 연결 상태 확인
# =====================================================

def check_database():
    """
    PostgreSQL 및 PostGIS 연결 테스트.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    PostGIS_Version()
                """
            )

            db_name, db_user, postgis_version = (
                cur.fetchone()
            )

    return {
        "database": db_name,
        "user": db_user,
        "postgis_version": postgis_version,
    }
