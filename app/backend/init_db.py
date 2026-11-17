
from pathlib import Path

import psycopg

from db import get_connection, check_database


BASE_DIR = Path(__file__).resolve().parent

SCHEMA_PATH = (
    BASE_DIR
    / "sql"
    / "001_initial_schema.sql"
)

EXPECTED_TABLES = {
    "reports",
    "risk_snapshots",
    "risk_locations",
    "risk_edge_scores",
}


def initialize_database():
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"SQL 파일이 없습니다: {SCHEMA_PATH}"
        )

    print("PostgreSQL 연결 확인 중...", flush=True)

    info = check_database()

    print(f"DB: {info['database']}")
    print(f"계정: {info['user']}")
    print(
        f"PostGIS: {info['postgis_version']}"
    )

    print("초기 테이블 생성 중...", flush=True)

    schema_sql = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    # 전체 스키마를 하나의 트랜잭션으로 실행
    with get_connection() as conn:
        conn.execute(schema_sql)

    # 생성 결과 확인
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name
                """,
                (list(EXPECTED_TABLES),),
            )

            actual_tables = {
                row[0]
                for row in cur.fetchall()
            }

    missing = EXPECTED_TABLES - actual_tables

    if missing:
        raise RuntimeError(
            f"생성되지 않은 테이블: {missing}"
        )

    print()
    print("13단계 초기 테이블 생성 완료")

    for table in sorted(actual_tables):
        print(f" - {table}")


if __name__ == "__main__":
    try:
        initialize_database()

    except psycopg.Error as error:
        print(
            "데이터베이스 오류:",
            error,
            flush=True,
        )
        raise
