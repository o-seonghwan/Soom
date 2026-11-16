
from uuid import UUID

from db import get_connection
from report_schemas import ReportCreate, ReportReview


# =========================================
# 1. 공통 조회 컬럼
# =========================================

REPORT_COLUMNS = """
    id,
    report_type,
    ST_Y(location) AS lat,
    ST_X(location) AS lng,
    observed_at,
    description,
    status,
    created_at,
    reviewed_at,
    review_note
"""


# =========================================
# 2. DB 행을 API 응답으로 변환
# =========================================

def row_to_report(row, include_review=False):
    result = {
        "id": str(row[0]),
        "type": row[1],
        "location": [
            float(row[2]),
            float(row[3]),
        ],
        "observedAt": row[4],
        "description": row[5],
        "status": row[6],
        "createdAt": row[7],
    }

    if include_review:
        result["reviewedAt"] = row[8]
        result["reviewNote"] = row[9]

    return result


# =========================================
# 3. 제보 등록 (기존 기능 유지)
# =========================================

def insert_report(report: ReportCreate):
    lat, lng = report.location

    sql = f"""
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
        RETURNING {REPORT_COLUMNS}
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    report.type,
                    lng,
                    lat,
                    report.observedAt,
                    report.description,
                ),
            )

            row = cur.fetchone()

            if row is None:
                raise RuntimeError(
                    "제보 등록 결과를 가져오지 못했습니다."
                )

            result = row_to_report(row)

    return result


# =========================================
# 4. 공개 제보 조회
# =========================================

def select_public_reports(limit=500):
    """
    승인된 제보만 공개한다.

    원본 설명은 공개하지 않고
    좌표를 소수점 셋째 자리로 반올림한다.

    원본 정확한 좌표는 DB에 그대로 유지.
    """

    sql = f"""
        SELECT {REPORT_COLUMNS}
        FROM public.reports
        WHERE status = 'verified'
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    result = []

    for row in rows:
        report = row_to_report(row)

        # 공개 위치는 대략적인 위치만 표시
        lat, lng = report["location"]
        report["location"] = [
            round(lat, 3),
            round(lng, 3),
        ]

        # 제보자의 자유 입력 내용 비공개
        report["description"] = ""

        result.append(report)

    return result


# =========================================
# 5. 관리자 전체 제보 조회
# =========================================

def select_admin_reports(limit=500):
    sql = f"""
        SELECT {REPORT_COLUMNS}
        FROM public.reports
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()

    return [
        row_to_report(row, include_review=True)
        for row in rows
    ]


# =========================================
# 6. 관리자 제보 상태 변경
# =========================================

def update_report_review(
    report_id: UUID,
    review: ReportReview,
):
    """
    승인 또는 반려 결과를 DB에 저장.

    정상 종료 시 COMMIT.
    해당 ID가 없으면 None 반환.
    """

    sql = f"""
        UPDATE public.reports
        SET
            status = %s,
            review_note = %s,
            reviewed_at = NOW(),
            updated_at = NOW()
        WHERE id = %s
        RETURNING {REPORT_COLUMNS}
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    review.status,
                    review.reviewNote,
                    report_id,
                ),
            )

            row = cur.fetchone()

            if row is None:
                return None

            result = row_to_report(
                row,
                include_review=True,
            )

    return result
