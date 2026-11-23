
import os
from pathlib import Path

import networkx as nx
import osmnx as ox

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import substring


# =====================================================
# 1. 경로 및 기본 설정
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

# 기존 로컬 개발용 보행 그래프 경로
DEFAULT_GRAPH_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "walking_network"
    / "gangnam_walk.graphml"
)

# 환경변수가 설정되면 해당 경로 사용
# 설정되지 않으면 기존 로컬 경로 유지
GRAPH_PATH = Path(
    os.getenv("LUNG_GRAPH_PATH") or str(DEFAULT_GRAPH_PATH)
).expanduser()

# 클릭 위치와 가장 가까운 보행 링크 사이 허용 거리
MAX_SNAP_DISTANCE_M = 200

# 예상 보행 속도: 1.25m/s (4.5km/h)
WALKING_SPEED_MPS = 1.25

# 같은 물리적 보행로의 역방향 링크 판별 허용 오차
REVERSE_EDGE_TOLERANCE_M = 1.5

# 경로 계산에서 사용하는 임시 노드 ID
START_NODE = "__route_start__"
END_NODE = "__route_end__"


# =====================================================
# 2. 보행 네트워크 로드
# =====================================================

def load_walking_graph():
    """
    서버 시작 시 GraphML 파일을 한 번 불러온다.

    A* 계산과 링크 거리 측정을 위해
    미터 단위 좌표계로 투영한다.
    """

    if not GRAPH_PATH.exists():
        raise FileNotFoundError(
            f"보행 네트워크 파일이 없습니다: {GRAPH_PATH}\n"
            "download_network.py를 먼저 실행하세요."
        )

    print("강남구 보행 네트워크 로딩 중...", flush=True)

    graph = ox.load_graphml(filepath=GRAPH_PATH)

    # 위경도 그래프를 거리 계산용 투영 좌표계로 변환
    graph = ox.project_graph(
        graph,
        to_crs="EPSG:5179",
    )

    print(
        f"그래프 로딩 완료: "
        f"노드 {len(graph.nodes):,}개 / "
        f"링크 {len(graph.edges):,}개",
        flush=True,
    )

    return graph


# =====================================================
# 3. 좌표 및 링크 보조 함수
# =====================================================

def get_transformers(graph):
    """
    위경도 -> 그래프 좌표계
    그래프 좌표계 -> 위경도
    """

    crs = graph.graph["crs"]

    to_graph = Transformer.from_crs(
        "EPSG:4326",
        crs,
        always_xy=True,
    )

    to_wgs84 = Transformer.from_crs(
        crs,
        "EPSG:4326",
        always_xy=True,
    )

    return to_graph, to_wgs84


def get_edge_line(graph, u, v, data):
    """
    간선의 실제 선형 geometry를 가져온다.

    geometry가 없는 간선은 양 끝 노드로 생성한다.
    선형 방향은 항상 u -> v로 정렬한다.
    """

    geometry = data.get("geometry")

    if geometry is None:
        geometry = LineString([
            (graph.nodes[u]["x"], graph.nodes[u]["y"]),
            (graph.nodes[v]["x"], graph.nodes[v]["y"]),
        ])

    points = list(geometry.coords)

    u_x = graph.nodes[u]["x"]
    u_y = graph.nodes[u]["y"]

    first_distance = (
        (points[0][0] - u_x) ** 2
        + (points[0][1] - u_y) ** 2
    )

    last_distance = (
        (points[-1][0] - u_x) ** 2
        + (points[-1][1] - u_y) ** 2
    )

    if last_distance < first_distance:
        points.reverse()

    return LineString(points)


def get_nearest_edge(graph, point, to_graph):
    """
    가장 가까운 보행 링크와 실제 접속점을 구한다.

    point: [위도, 경도]
    """

    x, y = to_graph.transform(
        point[1],
        point[0],
    )

    edge_id, distance = ox.distance.nearest_edges(
        graph,
        X=x,
        Y=y,
        return_dist=True,
    )

    u, v, key = edge_id
    edge_data = graph.get_edge_data(u, v, key)

    line = get_edge_line(
        graph,
        u,
        v,
        edge_data,
    )

    clicked_point = Point(x, y)

    # 링크 상의 최단 투영 위치
    position = line.project(clicked_point)
    snapped_point = line.interpolate(position)

    if distance > MAX_SNAP_DISTANCE_M:
        raise ValueError(
            f"선택 위치에서 가장 가까운 보행로까지 "
            f"{distance:.1f}m 떨어져 있습니다. "
            "보행로 근처를 선택하세요."
        )

    return {
        "edge": edge_id,
        "line": line,
        "point": snapped_point,
        "distance": float(distance),
    }


# =====================================================
# 4. 동일한 보행 링크의 양방향 간선 검색
# =====================================================

def get_matching_edges(graph, snap):
    """
    선택된 보행 링크와 동일한 실제 선형을 갖는
    정방향 및 역방향 링크를 찾는다.

    역방향 링크가 존재하지 않으면 생성하지 않는다.
    """

    u, v, key = snap["edge"]

    candidates = [(u, v, key)]
    result = []

    # 역방향 링크 확인
    if graph.has_edge(v, u):
        for reverse_key, data in graph[v][u].items():
            reverse_line = get_edge_line(
                graph,
                v,
                u,
                data,
            )

            # 같은 물리적 경로인지 geometry로 확인
            if (
                reverse_line.hausdorff_distance(
                    snap["line"]
                )
                <= REVERSE_EDGE_TOLERANCE_M
            ):
                candidates.append((v, u, reverse_key))

    for edge_id in candidates:
        eu, ev, ek = edge_id
        data = graph.get_edge_data(eu, ev, ek)
        line = get_edge_line(graph, eu, ev, data)

        result.append({
            "edge": edge_id,
            "data": data,
            "line": line,
        })

    return result


# =====================================================
# 5. 보행 링크의 일부 구간 생성
# =====================================================

def create_partial_edge(
    graph,
    from_node,
    to_node,
    edge_info,
    start_position,
    end_position,
):
    """
    링크의 일부를 임시 간선으로 생성한다.

    원래 링크 길이에 실제 선형의 비율을 적용한다.
    """

    line = edge_info["line"]
    original_length = float(
        edge_info["data"]["length"]
    )

    line_length = line.length

    if line_length <= 0:
        raise ValueError(
            "길이가 0인 보행 링크를 발견했습니다."
        )

    start_position = max(
        0.0,
        min(start_position, line_length),
    )

    end_position = max(
        0.0,
        min(end_position, line_length),
    )

    if end_position < start_position:
        raise ValueError(
            "보행 링크 진행 방향이 잘못되었습니다."
        )

    partial_geometry = substring(
        line,
        start_position,
        end_position,
    )

    # 0m 길이의 접속점도 유효한 간선으로 처리
    if isinstance(partial_geometry, Point):
        xy = partial_geometry.coords[0]
        partial_geometry = LineString([xy, xy])

    fraction = (
        (end_position - start_position)
        / line_length
    )

    partial_length = original_length * fraction

    graph.add_edge(
        from_node,
        to_node,
        length=partial_length,
        geometry=partial_geometry,
        # Resolve the model score for a partial link from its original link.
        source_edge=edge_info["edge"],
    )


# =====================================================
# 6. 출발지와 목적지 가상 노드 연결
# =====================================================

def connect_virtual_nodes(graph, start_snap, end_snap):
    """
    경로마다 생성하는 임시 그래프에
    시작점과 도착점을 연결한다.

    원본 보행 네트워크는 변경하지 않는다.
    """

    route_graph = nx.MultiDiGraph(graph)

    start_point = start_snap["point"]
    end_point = end_snap["point"]

    # 가상 노드 생성
    route_graph.add_node(
        START_NODE,
        x=start_point.x,
        y=start_point.y,
    )

    route_graph.add_node(
        END_NODE,
        x=end_point.x,
        y=end_point.y,
    )

    start_edges = get_matching_edges(
        graph,
        start_snap,
    )

    end_edges = get_matching_edges(
        graph,
        end_snap,
    )

    # 1. 출발점 -> 링크 진행 방향의 끝 노드
    for edge_info in start_edges:
        u, v, key = edge_info["edge"]
        line = edge_info["line"]

        position = line.project(start_point)

        create_partial_edge(
            route_graph,
            START_NODE,
            v,
            edge_info,
            position,
            line.length,
        )

    # 2. 링크 시작 노드 -> 도착점
    for edge_info in end_edges:
        u, v, key = edge_info["edge"]
        line = edge_info["line"]

        position = line.project(end_point)

        create_partial_edge(
            route_graph,
            u,
            END_NODE,
            edge_info,
            0.0,
            position,
        )

    # 3. 출발지와 목적지가 같은 링크 위에 있는 경우
    #    교차점까지 돌아가지 않고 직접 이동할 수 있도록 연결
    for start_edge in start_edges:
        for end_edge in end_edges:
            if start_edge["edge"] != end_edge["edge"]:
                continue

            line = start_edge["line"]

            start_position = line.project(start_point)
            end_position = line.project(end_point)

            # 링크의 실제 진행 방향을 따라 이동 가능한 경우
            if start_position <= end_position + 1e-7:
                create_partial_edge(
                    route_graph,
                    START_NODE,
                    END_NODE,
                    start_edge,
                    start_position,
                    end_position,
                )

    return route_graph


# =====================================================
# 7. A* 경로를 지도 좌표로 변환
# =====================================================

def link_clean_index(edge_risks, u, v, key, edge_data):
    """The model score belongs to the exact directed walking link."""
    if not edge_risks:
        return None

    source = edge_data.get("source_edge", (u, v, key))
    risk = edge_risks.get(tuple(source))

    if risk is None or risk.get("cleanIndex") is None:
        return None

    return round(float(risk["cleanIndex"]), 2)


def route_to_coordinates(
    graph,
    route_nodes,
    to_wgs84,
    edge_risks=None,
):
    """
    계산된 A* 노드 목록을
    지도 표시용 위경도 배열로 변환한다.
    """

    coordinates = []
    total_distance = 0.0
    segments = []

    if len(route_nodes) == 1:
        node = graph.nodes[route_nodes[0]]
        lon, lat = to_wgs84.transform(
            node["x"],
            node["y"],
        )
        return [[lat, lon]], 0.0, segments

    for u, v in zip(
        route_nodes[:-1],
        route_nodes[1:],
    ):
        # A*가 선택한 병렬 간선 중 최소 거리 간선
        edges = graph.get_edge_data(u, v)

        key, edge = min(
            edges.items(),
            key=lambda item: float(
                item[1]["length"]
            ),
        )

        total_distance += float(edge["length"])

        line = get_edge_line(
            graph,
            u,
            v,
            edge,
        )

        segment = []

        for x, y in line.coords:
            lon, lat = to_wgs84.transform(x, y)
            segment.append([lat, lon])

        # Keep each original edge geometry separate for correct color boundaries.
        segments.append({
            "coordinates": segment,
            "cleanIndex": link_clean_index(
                edge_risks, u, v, key, edge
            ),
        })

        # 중복되는 경로 연결점 제거
        if coordinates and segment:
            last = coordinates[-1]
            first = segment[0]

            if (
                abs(last[0] - first[0]) < 1e-8
                and abs(last[1] - first[1]) < 1e-8
            ):
                segment = segment[1:]

        coordinates.extend(segment)

    return coordinates, total_distance, segments


# =====================================================
# 8. A* 일반 최단경로 계산
# =====================================================

def calculate_shortest_route(
    graph,
    start,
    end,
    edge_risks=None,
):
    """
    강남구 보행 링크 기반 A* 최단경로.

    일반 경로이므로 위험도는 사용하지 않는다.
    """

    # 위경도 -> 투영 좌표계 변환기
    to_graph, to_wgs84 = get_transformers(graph)

    # 1. 출발지와 목적지를 가까운 보행 링크에 투영
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

    # 2. 임시 출발·도착 노드가 연결된 그래프 생성
    route_graph = connect_virtual_nodes(
        graph,
        start_snap,
        end_snap,
    )

    # 3. A* 휴리스틱: 목적지까지의 거리
    # 투영 좌표계 왜곡을 고려한 보수적인 계수
    def heuristic(node_a, node_b):
        a = route_graph.nodes[node_a]
        b = route_graph.nodes[node_b]

        dx = a["x"] - b["x"]
        dy = a["y"] - b["y"]

        return 0.95 * (dx * dx + dy * dy) ** 0.5

    # 4. 실제 A* 최단경로 탐색
    route_nodes = nx.astar_path(
        route_graph,
        source=START_NODE,
        target=END_NODE,
        heuristic=heuristic,
        weight="length",
    )

    # 5. 노드 경로 -> 실제 보행 링크 선형 변환
    coordinates, total_distance, segments = route_to_coordinates(
        route_graph,
        route_nodes,
        to_wgs84,
        edge_risks,
    )

    # 6. 접속점 좌표 반환
    start_lon, start_lat = to_wgs84.transform(
        start_snap["point"].x,
        start_snap["point"].y,
    )

    end_lon, end_lat = to_wgs84.transform(
        end_snap["point"].x,
        end_snap["point"].y,
    )

    # 7. 보행 예상 시간 (분)
    estimated_minutes = (
        total_distance / WALKING_SPEED_MPS / 60
    )

    return {
        "id": "shortest",
        "name": "일반 최단 도보 경로",
        "distanceM": round(total_distance),
        "estimatedMinutes": round(
            estimated_minutes,
            1,
        ),
        "coordinates": coordinates,
        "segments": segments,

        # 원래 클릭 위치가 아닌 실제 링크 접속점
        "snappedStart": [start_lat, start_lon],
        "snappedEnd": [end_lat, end_lon],

        # 클릭 지점과 보행 링크 사이의 직선거리
        "startSnapDistanceM": round(
            start_snap["distance"],
            1,
        ),
        "endSnapDistanceM": round(
            end_snap["distance"],
            1,
        ),
    }
