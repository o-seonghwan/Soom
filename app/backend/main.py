
from contextlib import asynccontextmanager

import networkx as nx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from walking_router import (
    load_walking_graph,
    calculate_shortest_route,
)


# 서버 시작 시 실행되는 함수
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 저장된 보행 네트워크를 메모리에 한 번 로드
    app.state.walking_graph = load_walking_graph()

    yield

    # 서버 종료 시 메모리 참조 해제
    app.state.walking_graph = None


app = FastAPI(
    title="폐(Lung) 끼치지 마세요 - 강남구 도보 경로 API",
    version="0.2.0",
    lifespan=lifespan,
)

# React 개발 서버 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RouteRequest(BaseModel):
    start: tuple[float, float] = Field(
        description="[위도, 경도]"
    )

    end: tuple[float, float] = Field(
        description="[위도, 경도]"
    )

    avoidanceLevel: Literal[
        "low", "medium", "high"
    ] = "medium"


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "gangnam-walking-route",
        "graph_loaded": (
            app.state.walking_graph is not None
        ),
    }


@app.post("/api/routes/shortest")
def shortest_route(
    request: RouteRequest,
    http_request: Request,
):
    # 위경도 유효성 검증
    for lat, lon in [request.start, request.end]:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(
                status_code=422,
                detail="유효하지 않은 위경도입니다.",
            )

    try:
        graph = http_request.app.state.walking_graph

        route = calculate_shortest_route(
            graph=graph,
            start=request.start,
            end=request.end,
        )

        return {
            "routes": [route]
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except (nx.NetworkXNoPath, nx.NodeNotFound):
        raise HTTPException(
            status_code=404,
            detail="연결된 보행 경로를 찾지 못했습니다.",
        )

    except Exception as error:
        print("경로 계산 오류:", repr(error), flush=True)

        raise HTTPException(
            status_code=503,
            detail="보행 경로 계산에 실패했습니다.",
        )
