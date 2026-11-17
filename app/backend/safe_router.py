
import math

import networkx as nx
from pyproj import Transformer
from shapely.geometry import Point

from risk_decay import effective_risk

from walking_router import (
    START_NODE,
    END_NODE,
    WALKING_SPEED_MPS,
    get_transformers,
    get_nearest_edge,
    get_edge_line,
    connect_virtual_nodes,
)


# =====================================================
# 1. 회피 강도별 가중치
# =====================================================

AVOIDANCE_WEIGHTS = {
    "low": 0.5,
    "medium": 2.0,
    "high": 6.0,
}


# =====================================================
# 2. 위험지역의 공간 객체 생성
# =====================================================

def build_risk_areas(graph, risk_locations):
    """
    위치별 위험도 데이터로 미터 단위
    영향 영역을 생성한다.

    기존 링크의 위험도는 11단계 매핑 결과 사용.
    여기서는 임시 접속 링크의 위험도 계산에 사용.
    """

    transformer = Transformer.from_crs(
        "EPSG:4326",
        graph.graph["crs"],
        always_xy=True,
    )

    areas = []

    for risk in risk_locations:
        x, y = transformer.transform(
            float(risk["lng"]),
            float(risk["lat"]),
        )

        area = Point(x, y).buffer(
            float(risk["radiusM"])
        )

        areas.append({
            "geometry": area,
            "center": Point(x, y),
            "score": float(risk["score"]),
            "isModel": risk.get("decayProfile") == "model-v1",
        })

    return areas


# =====================================================
# 3. 임시 접속 링크의 위험도 계산
# =====================================================

def virtual_edge_risks(
    route_graph,
    risk_areas,
):
    """
    출발지·목적지 연결에 생성된 임시 링크의
    위험도를 계산한다.

    링크 일부가 위험영역에 닿으면 최대 점수 적용.
    """

    result = {}

    for u, v, key, data in route_graph.edges(
        keys=True,
        data=True,
    ):
        # 원본 링크는 이미 risk_mapper에서 계산함
        if (
            u != START_NODE
            and v != START_NODE
            and u != END_NODE
            and v != END_NODE
        ):
            continue

        line = get_edge_line(
            route_graph, u, v, data
        )

        score = 0.0

        for risk in risk_areas:
            if line.intersects(risk["geometry"]):
                contribution = (
                    effective_risk(risk["score"], line.distance(risk["center"]))
                    if risk["isModel"] else risk["score"]
                )
                score = max(score, contribution)

        result[(u, v, key)] = score / 100.0

    return result


# =====================================================
# 4. 링크별 위험 비용 계산
# =====================================================

def calculate_edge_cost(
    u,
    v,
    key,
    data,
    edge_risks,
    temporary_risks,
    risk_weight,
):
    """
    일반 거리 × (1 + 회피강도 × 정규화 위험도)
    """

    length = float(data["length"])

    edge_id = (u, v, key)

    if edge_id in temporary_risks:
        risk = temporary_risks[edge_id]

    else:
        risk_data = edge_risks.get(edge_id, {})
        risk = float(
            risk_data.get("normalizedRisk", 0.0)
        )

    return length * (
        1.0 + risk_weight * risk
    )


# =====================================================
# 5. A* 경로 좌표 및 거리 변환
# =====================================================

def build_route_result(
    route_graph,
    route_nodes,
    to_wgs84,
    edge_risks,
    temporary_risks,
    risk_weight,
):
    """
    A*가 선택한 비용이 가장 낮은 실제 링크를
    이용해 지도용 좌표와 실제 거리를 생성한다.
    """

    coordinates = []
    total_distance = 0.0

    for u, v in zip(
        route_nodes[:-1],
        route_nodes[1:],
    ):
        edges = route_graph.get_edge_data(u, v)

        # A*에 적용한 비용과 동일한 기준
        key, edge_data = min(
            edges.items(),
            key=lambda item: calculate_edge_cost(
                u,
                v,
                item[0],
                item[1],
                edge_risks,
                temporary_risks,
                risk_weight,
            ),
        )

        total_distance += float(
            edge_data["length"]
        )

        line = get_edge_line(
            route_graph,
            u,
            v,
            edge_data,
        )

        segment = []

        for x, y in line.coords:
            lon, lat = to_wgs84.transform(
                x, y
            )
            segment.append([lat, lon])

        if coordinates and segment:
            last = coordinates[-1]
            first = segment[0]

            if (
                abs(last[0] - first[0]) < 1e-8
                and abs(last[1] - first[1]) < 1e-8
            ):
                segment = segment[1:]

        coordinates.extend(segment)

    return coordinates, total_distance


# =====================================================
# 6. 위험 회피 A* 경로 탐색
# =====================================================

def calculate_safest_route(
    graph,
    start,
    end,
    avoidance_level,
    edge_risks,
    risk_locations,
):
    """
    강남구 보행 네트워크 기반 위험 회피 A*.

    일반 A*와 동일한 그래프를 사용하지만
    거리 + 위험 가중치를 최소화한다.

    원본 그래프와 원본 edge_risks는 변경하지 않음.
    """

    if isinstance(avoidance_level, str):
        if avoidance_level not in AVOIDANCE_WEIGHTS:
            raise ValueError("올바르지 않은 회피 강도입니다.")
        risk_weight = AVOIDANCE_WEIGHTS[avoidance_level]
    else:
        # 0~100 continuous slider mapped linearly to an A* risk multiplier.
        # 0 means distance-only; 100 has the former "high" intensity (6.0).
        value = float(avoidance_level)
        if not math.isfinite(value) or not (0 <= value <= 100):
            raise ValueError("회피 강도는 0~100 사이여야 합니다.")
        risk_weight = 6.0 * value / 100.0

    # 1. 좌표 변환기
    to_graph, to_wgs84 = get_transformers(
        graph
    )

    # 2. 출발지·목적지 보행 링크 접속점 탐색
    start_snap = get_nearest_edge(
        graph,
        start,
        to_graph,
    )

    end_snap = get_nearest_edge(
        graph,
        end,
        to_graph,
    )

    # 3. 임시 출발·도착 노드 연결
    route_graph = connect_virtual_nodes(
        graph,
        start_snap,
        end_snap,
    )

    # 4. 임시 접속 링크의 위험도 계산
    risk_areas = build_risk_areas(
        graph,
        risk_locations,
    )

    temporary_risks = virtual_edge_risks(
        route_graph,
        risk_areas,
    )

    # 5. MultiDiGraph 전용 가중치
    # 두 노드 사이 여러 링크 중 최소 위험비용 선택
    def weight_function(u, v, edge_bundle):
        return min(
            calculate_edge_cost(
                u,
                v,
                key,
                data,
                edge_risks,
                temporary_risks,
                risk_weight,
            )
            for key, data in edge_bundle.items()
        )

    # 6. A* 휴리스틱
    # 0을 사용해 위험 비용에 대한 과대추정을 방지
    # A*는 이 경우 다익스트라와 동일한 방식으로 탐색
    def heuristic(node_a, node_b):
        return 0.0

    # 7. 위험 회피 경로 계산
    route_nodes = nx.astar_path(
        route_graph,
        source=START_NODE,
        target=END_NODE,
        heuristic=heuristic,
        weight=weight_function,
    )

    # 8. 실제 보행 링크 경로 좌표 생성
    coordinates, total_distance = build_route_result(
        route_graph,
        route_nodes,
        to_wgs84,
        edge_risks,
        temporary_risks,
        risk_weight,
    )

    # 9. 보행 접속점 좌표
    start_lon, start_lat = to_wgs84.transform(
        start_snap["point"].x,
        start_snap["point"].y,
    )

    end_lon, end_lat = to_wgs84.transform(
        end_snap["point"].x,
        end_snap["point"].y,
    )

    # 10. 예상 이동 시간
    estimated_minutes = (
        total_distance / WALKING_SPEED_MPS / 60
    )

    return {
        "id": "safest",
        "name": "간접흡연 위험 회피 경로",
        "distanceM": round(total_distance),
        "estimatedMinutes": round(
            estimated_minutes, 1
        ),
        "coordinates": coordinates,
        "snappedStart": [
            start_lat,
            start_lon,
        ],
        "snappedEnd": [
            end_lat,
            end_lon,
        ],
        "startSnapDistanceM": round(
            start_snap["distance"], 1
        ),
        "endSnapDistanceM": round(
            end_snap["distance"], 1
        ),
    }
