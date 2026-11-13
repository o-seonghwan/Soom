
from datetime import datetime, timezone

from db import get_connection, check_database


# =====================================================
# 1. 테스트 좌표 설정
# =====================================================

# 강남역 인근 테스트 위치
TEST_LAT = 37.4979
TEST_LNG = 127.0276


# =====================================================
# 2. 데이터베이스 테스트
# =====================================================

def main():
    print("=" * 50)
    print("13단계 PostgreSQL 제보 INSERT/SELECT 테스트")
    print("=" * 50)

    # PostgreSQL 및 PostGIS 연결 확인
    info = check_database()

    print(f"데이터베이스: {info['database']}")
    print(f"연결 계정: {info['user']}")
    print(f"PostGIS: {info['postgis_version']}")

    # 트랜잭션 시작
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # -----------------------------------------
            # 1. 테이블 생성 여부 확인
            # -----------------------------------------

            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN (
                      'reports',
                      'risk_snapshots',
                      'risk_locations',
                      'risk_edge_scores'
                  )
            """)

            table_count = cur.fetchone()[0]

            print(f"프로젝트 테이블: {table_count}/4개")

            if table_count != 4:
                raise RuntimeError(
                    "DB 초기화가 완료되지 않았습니다."
                )

            # -----------------------------------------
            # 2. PostGIS 공간 좌표 테스트
            # -----------------------------------------

            cur.execute("""
                SELECT
                    ST_Y(
                        ST_SetSRID(
                            ST_MakePoint(%s, %s),
                            4326
                        )
                    ),
                    ST_X(
                        ST_SetSRID(
                            ST_MakePoint(%s, %s),
                            4326
                        )
                    )
            """, (
                TEST_LNG,
                TEST_LAT,
                TEST_LNG,
                TEST_LAT
            ))

            lat, lng = cur.fetchone()

            assert abs(lat - TEST_LAT) < 1e-8
            assert abs(lng - TEST_LNG) < 1e-8

            print("PostGIS 좌표 변환: 성공")

            # -----------------------------------------
            # 3. 테스트 제보 INSERT
            # -----------------------------------------

            cur.execute("""
                INSERT INTO public.reports (
                    report_type,
                    location,
                    observed_at,
                    description
                )
                VALUES (
                    %s,
                    ST_SetSRID(
                        ST_MakePoint(%s, %s),
                        4326
                    ),
                    %s,
                    %s
                )
                RETURNING id
            """, (
                "smoking",
                TEST_LNG,
                TEST_LAT,
                datetime.now(timezone.utc),
                "13단계 DB 테스트 제보"
            ))

            report_id = cur.fetchone()[0]

            print(f"제보 INSERT: 성공 ({report_id})")

            # -----------------------------------------
            # 4. 저장한 제보 SELECT
            # -----------------------------------------

            cur.execute("""
                SELECT
                    report_type,
                    ST_Y(location),
                    ST_X(location),
                    status
                FROM public.reports
                WHERE id = %s
            """, (report_id,))

            row = cur.fetchone()

            if row is None:
                raise RuntimeError(
                    "저장한 제보를 조회할 수 없습니다."
                )

            report_type, lat, lng, status = row

            assert report_type == "smoking"
            assert status == "pending"
            assert abs(lat - TEST_LAT) < 1e-8
            assert abs(lng - TEST_LNG) < 1e-8

            print("제보 SELECT: 성공")
            print(f"제보 상태: {status}")

        print()
        print("모든 테스트 성공!")

    finally:
        # INSERT한 테스트 데이터 저장 취소
        conn.rollback()
        conn.close()

        print("테스트 데이터 ROLLBACK 완료")


if __name__ == "__main__":
    main()
