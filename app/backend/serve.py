"""Serve the existing Soom FastAPI routes before the GraphML is ready.

The walking graph is loaded asynchronously once the bootstrap downloader
has created the persistent GraphML file. No placeholder routing results
are returned while graph data is unavailable.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Request
from fastapi.responses import JSONResponse

from main import app
from risk_provider import get_risk_snapshot
from risk_mapper import map_risks_to_edges, summarize_edge_risks
from b2g_cleanliness import edge_cleanliness_geojson
from walking_router import GRAPH_PATH, load_walking_graph


logger = logging.getLogger("soom.bootstrap")

GRAPH_REQUIRED_PATHS = {
    "/api/routes",
    "/api/routes/shortest",
    "/api/risks/edges",
    "/api/b2g/cleanliness/edges",
}


async def prepare_graph():
    """Retry GraphML loading after the independent download has finished."""
    while True:
        if not GRAPH_PATH.is_file():
            await asyncio.sleep(10)
            continue

        try:
            graph = await asyncio.to_thread(load_walking_graph)
            snapshot = app.state.risk_snapshot
            edge_risks = await asyncio.to_thread(
                map_risks_to_edges,
                graph=graph,
                risk_locations=snapshot["locations"],
            )
            if snapshot["source"] == "model-csv" and not edge_risks:
                raise ValueError("모델 CSV가 보행 링크와 매칭되지 않았습니다.")

            cleanliness = await asyncio.to_thread(
                edge_cleanliness_geojson, graph, edge_risks
            )

            app.state.walking_graph = graph
            app.state.edge_risks = edge_risks
            app.state.b2g_cleanliness = cleanliness
            summary = summarize_edge_risks(graph=graph, edge_risks=edge_risks)
            logger.info(
                "GraphML ready: nodes=%d edges=%d affected=%d source=%s",
                len(graph.nodes),
                len(graph.edges),
                summary["affectedEdges"],
                snapshot["source"],
            )
            return
        except Exception:
            logger.exception("GraphML initialization failed; retrying")
            await asyncio.sleep(30)


@asynccontextmanager
async def responsive_lifespan(application):
    application.state.walking_graph = None
    application.state.edge_risks = {}
    application.state.b2g_cleanliness = {"type": "FeatureCollection", "features": []}
    application.state.risk_snapshot = get_risk_snapshot()

    task = asyncio.create_task(prepare_graph())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.middleware("http")
async def guard_graph_routes(request: Request, call_next):
    if (
        request.url.path in GRAPH_REQUIRED_PATHS
        and request.app.state.walking_graph is None
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "보행 네트워크를 준비 중입니다. GraphML 로딩이 완료되면 다시 시도하세요.",
                "graph_loaded": False,
            },
        )
    return await call_next(request)


@app.get("/", include_in_schema=False)
def service_home(request: Request):
    """Human-readable entry point for the public backend domain."""
    return {
        "service": "Soom API",
        "status": "running",
        "graph_loaded": request.app.state.walking_graph is not None,
        "health": "/api/health",
        "docs": "/docs",
    }


app.router.lifespan_context = responsive_lifespan
