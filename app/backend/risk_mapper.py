
import osmnx as ox

from pyproj import Transformer
from shapely.geometry import Point


# =====================================================
# 1. 위험도와 보행 링크 매핑
# =====================================================

def map_risks_to_edges(graph, risk_locations):
    """
    위치별 위험도를 보행 링크에 연결한다.

    입력:
        graph: 투영 좌표계의 OSMnx MultiDiGraph
        risk_locations: 위치별 위험도 목록

    반환:
        {
            (u, v, key): {
                "score": 90.0,
                "normalizedRisk": 0.9,
                "riskIds": ["risk-1"]
            }
        }

    원본 graph는 수정하지 않는다.
    """

    # 경로 그래프의 좌표계 확인
    graph_crs = graph.graph["crs"]

    if not graph_crs.is_projected:
        raise ValueError(
            "보행 그래프는 미터 단위의 "
            "투영 좌표계여야 합니다."
        )

    # WGS84 위경도 -> 그래프 좌표계
    transformer = Transformer.from_crs(
        "EPSG:4326",
        graph_crs,
        always_xy=True,
    )

    # 보행 링크를 GeoDataFrame으로 변환
    edges = ox.convert.graph_to_gdfs(
        graph,
        nodes=False,
        edges=True,
        fill_edge_geometry=True,
    )

    # 공간 인덱스 생성
    spatial_index = edges.sindex

    # 보행 링크 ID별 위험도
    edge_risks = {}

    # =================================================
    # 2. 위험 위치별 영향 범위 계산
    # =================================================

    for risk in risk_locations:
        risk_id = str(risk["id"])
        score = float(risk["score"])
        radius = float(risk["radiusM"])

        # 위경도 -> 미터 좌표계
        x, y = transformer.transform(
            float(risk["lng"]),
            float(risk["lat"]),
        )

        center = Point(x, y)

        # 임시 위험 영향 범위
        risk_area = center.buffer(radius)

        # 영향 범위와 교차하는 보행 링크 검색
        candidate_positions = spatial_index.query(
            risk_area,
            predicate="intersects",
        )

        for position in candidate_positions:
            # 실제 보행 링크 ID (u, v, key)
            edge_id = edges.index[int(position)]

            # 해당 링크의 선형 정보
            line = edges.geometry.iloc[int(position)]

            # 위험 영역과 겹치는지 최종 확인
            if not line.intersects(risk_area):
                continue

            # 최초 발견한 위험 링크
            if edge_id not in edge_risks:
                edge_risks[edge_id] = {
                    "score": score,
                    "normalizedRisk": score / 100.0,
                    "riskIds": [risk_id],
                }

            # 다른 위험지역과 중복되는 경우
            else:
                existing = edge_risks[edge_id]

                # 최대 위험점수 사용
                existing["score"] = max(
                    existing["score"],
                    score,
                )

                existing["normalizedRisk"] = (
                    existing["score"] / 100.0
                )

                if risk_id not in existing["riskIds"]:
                    existing["riskIds"].append(risk_id)

    return edge_risks


# =====================================================
# 3. 매핑 결과 요약
# =====================================================

def summarize_edge_risks(graph, edge_risks):
    """
    전체 링크 중 위험도가 연결된 링크를 집계한다.
    """

    total_edges = graph.number_of_edges()
    affected_edges = len(edge_risks)

    scores = [
        item["score"]
        for item in edge_risks.values()
    ]

    high_risk_edges = sum(
        score >= 80
        for score in scores
    )

    return {
        "totalEdges": total_edges,
        "affectedEdges": affected_edges,
        "highRiskEdges": high_risk_edges,
        "unaffectedEdges": (
            total_edges - affected_edges
        ),
    }


# =====================================================
# 4. API 반환용 링크 위험도 변환
# =====================================================

def serialize_edge_risks(edge_risks, limit=100):
    """
    내부의 (u, v, key) 형태를
    JSON으로 반환할 수 있는 형태로 변환한다.

    전체 데이터가 아니라 최대 limit개 반환.
    """

    result = []

    for edge_id, risk in list(
        edge_risks.items()
    )[:limit]:
        u, v, key = edge_id

        result.append({
            "u": str(u),
            "v": str(v),
            "key": str(key),
            "score": risk["score"],
            "normalizedRisk": risk["normalizedRisk"],
            "riskIds": risk["riskIds"],
        })

    return result
