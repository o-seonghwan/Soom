
from contextlib import asynccontextmanager
import os
from typing import Literal
from uuid import UUID

import networkx as nx
import psycopg

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status,
)

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from walking_router import (
    load_walking_graph,
    calculate_shortest_route,
)

from safe_router import calculate_safest_route
from b2g_cleanliness import edge_cleanliness_geojson
from dbscan_sites import load_dbscan_sites
from childcare_exposure import load_childcare_exposure
from risk_provider import get_risk_snapshot
from smoking_zones import load_smoking_zones
from address_lookup import reverse_address, search_addresses, forward_address
import requests

from risk_mapper import (
    map_risks_to_edges,
    summarize_edge_risks,
    serialize_edge_risks,
)

from report_schemas import (
    ReportCreate,
    ReportResponse,
    ReportReview,
    AdminReportResponse,
)

from report_repository import (
    insert_report,
    select_public_reports,
    select_admin_reports,
    update_report_review,
)

from admin_auth import require_admin, check_password, create_session, get_cookie_session, revoke_session, COOKIE_NAME, REMEMBER_SECONDS


# =========================================
# 1. 서버 시작 및 종료
# =========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("강남구 시스템 초기화 시작", flush=True)

    graph = load_walking_graph()
    snapshot = get_risk_snapshot()

    edge_risks = map_risks_to_edges(
        graph=graph,
        risk_locations=snapshot["locations"],
    )

    if snapshot["source"] == "model-csv" and not edge_risks:
        raise ValueError(
            "모델 CSV는 로딩됐으나 21m 이내에 매칭된 보행 링크가 없습니다. "
            "CSV 좌표계/분석범위와 보행 네트워크를 확인하세요."
        )

    app.state.walking_graph = graph
    app.state.risk_snapshot = snapshot
    app.state.edge_risks = edge_risks
    app.state.b2g_cleanliness = edge_cleanliness_geojson(graph, edge_risks)

    summary = summarize_edge_risks(
        graph=graph,
        edge_risks=edge_risks,
    )

    print(
        f"위험 위치: {len(snapshot['locations'])}개",
        flush=True,
    )
    print(
        f"위험 영향 링크: {summary['affectedEdges']}개",
        flush=True,
    )
    print("시스템 초기화 완료", flush=True)

    yield

    app.state.walking_graph = None
    app.state.risk_snapshot = None
    app.state.edge_risks = None
    app.state.b2g_cleanliness = None


# =========================================
# 2. FastAPI 초기화
# =========================================

app = FastAPI(
    title="폐(Lung) 끼치지 마세요 - 강남구 API",
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        *[origin.strip() for origin in os.getenv("ADMIN_ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-CSRF-Token",
    ],
)


# =========================================
# 3. 경로 요청 타입
# =========================================

class RouteRequest(BaseModel):
    start: tuple[float, float] = Field(
        description="[위도, 경도]"
    )

    end: tuple[float, float] = Field(
        description="[위도, 경도]"
    )

    # Numeric 0..100 for continuous slider; legacy enum kept for compatibility.
    avoidanceLevel: float | Literal["low", "medium", "high"] = Field(default=50, description="0~100 회피 강도")


# =========================================
# 4. 경로 요청 검증
# =========================================

def validate_route_request(request: RouteRequest):
    for lat, lon in [
        request.start,
        request.end,
    ]:
        if not (
            -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            raise HTTPException(
                status_code=422,
                detail="유효하지 않은 위경도입니다.",
            )


# =========================================
# 5. 경로 오류 처리
# =========================================

def handle_route_error(error):
    if isinstance(error, ValueError):
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if isinstance(
        error,
        (nx.NetworkXNoPath, nx.NodeNotFound),
    ):
        raise HTTPException(
            status_code=404,
            detail="연결된 보행 경로를 찾지 못했습니다.",
        ) from error

    print(
        "경로 계산 오류:",
        repr(error),
        flush=True,
    )

    raise HTTPException(
        status_code=503,
        detail="보행 경로 계산에 실패했습니다.",
    ) from error


# =========================================
# 6. 제보 DB 오류 처리
# =========================================

def handle_report_db_error(error):
    print(
        "제보 DB 오류:",
        repr(error),
        flush=True,
    )

    raise HTTPException(
        status_code=503,
        detail="제보 데이터베이스 처리에 실패했습니다.",
    ) from error


# =========================================
# 7. 기존 시스템 API
# =========================================

@app.get("/api/health")
def health(request: Request):
    return {
        "status": "ok",
        "service": "gangnam-walking-route",
        "graph_loaded": (
            request.app.state.walking_graph is not None
        ),
        "risk_source": (
            request.app.state.risk_snapshot["source"]
        ),
    }


@app.post("/api/routes/shortest")
def shortest_route(
    request: RouteRequest,
    http_request: Request,
):
    validate_route_request(request)

    try:
        graph = http_request.app.state.walking_graph

        route = calculate_shortest_route(
            graph=graph,
            start=request.start,
            end=request.end,
        )

        return {"routes": [route]}

    except Exception as error:
        handle_route_error(error)


@app.post("/api/routes")
def compare_routes(
    request: RouteRequest,
    http_request: Request,
):
    validate_route_request(request)

    graph = http_request.app.state.walking_graph
    edge_risks = http_request.app.state.edge_risks
    snapshot = http_request.app.state.risk_snapshot

    try:
        shortest = calculate_shortest_route(
            graph=graph,
            start=request.start,
            end=request.end,
            edge_risks=edge_risks,
        )

        safest = calculate_safest_route(
            graph=graph,
            start=request.start,
            end=request.end,
            avoidance_level=request.avoidanceLevel,
            edge_risks=edge_risks,
            risk_locations=snapshot["locations"],
        )

        return {
            "routes": [shortest, safest]
        }

    except Exception as error:
        handle_route_error(error)


@app.get("/api/reverse-address")
def reverse_address_api(lat: float, lng: float):
    """Server-side reverse-geocoding. Coordinates only, never send an API key to the browser."""
    try:
        return reverse_address(lat, lng)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail="주소 조회 서비스 연결에 실패했습니다.") from error


@app.get("/api/search-addresses")
def search_addresses_api(q: str):
    try:
        return {"suggestions": search_addresses(q)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail="주소 검색 서비스에 연결하지 못했습니다.") from error


@app.get("/api/geocode-address")
def geocode_address_api(q: str):
    try:
        return forward_address(q)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail="주소 변환 서비스에 연결하지 못했습니다.") from error


@app.get("/api/smoking-zones")
def smoking_zones():
    """Return declared smoking locations only; empty when no official CSV configured."""
    try:
        return load_smoking_zones()
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/risks")
def get_risks(request: Request):
    return request.app.state.risk_snapshot["locations"]


@app.get("/api/b2g/dbscan/sites")
def get_b2g_dbscan_sites(admin_username: str = Depends(require_admin)):
    """Return existing DBSCAN CSV outputs only; never synthesize site suggestions."""
    try:
        return load_dbscan_sites()
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/b2g/childcare/exposure")
def get_b2g_childcare_exposure(admin_username: str = Depends(require_admin)):
    """Only return the previously generated childcare ranking CSV."""
    try:
        return load_childcare_exposure()
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/b2g/cleanliness/edges")
def get_b2g_cleanliness_edges(request: Request):
    """B2G visualization must use actual model results, never Mock scores."""
    snapshot = request.app.state.risk_snapshot
    if snapshot["source"] != "model-csv":
        raise HTTPException(
            status_code=503,
            detail=(
                "B2G 청정지수는 AI 모델 결과만 표시합니다. "
                "LUNG_RISK_CSV에 1_위험지도_지점.csv의 전체 경로를 지정하고 "
                "백엔드를 재시작하세요."
            ),
        )
    return {
        **request.app.state.b2g_cleanliness,
        "source": "model-csv",
        "modelPointCount": len(snapshot["locations"]),
        "modelVersion": snapshot["version"],
    }


@app.get("/api/risks/edges")
def get_edge_risks(
    request: Request,
    limit: int = 100,
):
    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=422,
            detail="limit은 1~1000 사이여야 합니다.",
        )

    graph = request.app.state.walking_graph
    snapshot = request.app.state.risk_snapshot
    edge_risks = request.app.state.edge_risks

    return {
        "source": snapshot["source"],
        "version": snapshot["version"],
        "generatedAt": snapshot["generatedAt"],
        "summary": summarize_edge_risks(
            graph=graph,
            edge_risks=edge_risks,
        ),
        "edges": serialize_edge_risks(
            edge_risks,
            limit=limit,
        ),
    }


# =========================================
# 8. 공개 사용자 제보 API
# =========================================

@app.post(
    "/api/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(report: ReportCreate):
    try:
        return insert_report(report)
    except psycopg.Error as error:
        handle_report_db_error(error)


@app.get(
    "/api/reports",
    response_model=list[ReportResponse],
)
def get_reports(limit: int = 500):
    """
    승인된 제보만 공개 조회한다.
    """

    if not 1 <= limit <= 500:
        raise HTTPException(
            status_code=422,
            detail="limit은 1~500 사이여야 합니다.",
        )

    try:
        return select_public_reports(limit=limit)
    except psycopg.Error as error:
        handle_report_db_error(error)


# =========================================
# 9. 관리자 보안 쿠키 세션
# =========================================

class AdminLoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


def _check_admin_origin(request: Request):
    # Browser-origin check for cookie-authenticated state changing calls.
    from urllib.parse import urlparse
    origin = request.headers.get("origin")
    if not origin:
        return  # Non-browser clients still require the CSRF token.
    allowed = {
        "http://localhost:5173", "http://127.0.0.1:5173",
        f"{request.url.scheme}://{request.headers.get('host', '')}",
        *[v.strip() for v in os.getenv("ADMIN_ALLOWED_ORIGINS", "").split(",") if v.strip()],
    }
    if origin not in allowed:
        raise HTTPException(status_code=403, detail="관리자 요청의 출처가 허용되지 않았습니다.")


@app.post("/api/admin/session")
def create_admin_session(body: AdminLoginRequest, request: Request, response: Response):
    _check_admin_origin(request)
    user = check_password(body.username, body.password)
    token, info = create_session(user, body.remember)
    response.set_cookie(
        key=COOKIE_NAME, value=token,
        max_age=REMEMBER_SECONDS if body.remember else None,
        path="/api/admin", httponly=True,
        secure=os.getenv("ADMIN_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return info


@app.delete("/api/admin/session")
def delete_admin_session(request: Request, response: Response,
                         admin_username: str = Depends(require_admin)):
    _check_admin_origin(request)
    revoke_session(request)
    response.delete_cookie(key=COOKIE_NAME, path="/api/admin", samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False}


# =========================================
# 9. 관리자 로그인 확인 API
# =========================================

@app.get("/api/admin/me")
def admin_me(request: Request, admin_username: str = Depends(require_admin)):
    data = get_cookie_session(request)
    return {
        "authenticated": True,
        "username": admin_username,
        "csrfToken": data["csrf"],
        "expiresAt": data["exp"],
    }


# =========================================
# 10. 관리자 전체 제보 조회 API
# =========================================

@app.get(
    "/api/admin/reports",
    response_model=list[AdminReportResponse],
)
def get_admin_reports(
    limit: int = 500,
    admin_username: str = Depends(require_admin),
):
    if not 1 <= limit <= 500:
        raise HTTPException(
            status_code=422,
            detail="limit은 1~500 사이여야 합니다.",
        )

    try:
        return select_admin_reports(limit=limit)
    except psycopg.Error as error:
        handle_report_db_error(error)


# =========================================
# 11. 관리자 제보 승인·반려 API
# =========================================

@app.patch(
    "/api/admin/reports/{report_id}",
    response_model=AdminReportResponse,
)
def review_report(
    report_id: UUID,
    review: ReportReview,
    request: Request,
    admin_username: str = Depends(require_admin),
):
    _check_admin_origin(request)
    try:
        updated = update_report_review(
            report_id=report_id,
            review=review,
        )

    except psycopg.Error as error:
        handle_report_db_error(error)

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="해당 제보를 찾을 수 없습니다.",
        )

    return updated
