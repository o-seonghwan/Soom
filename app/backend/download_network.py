
import json
import time
from pathlib import Path

import osmnx as ox
from shapely.geometry import shape
from requests.exceptions import RequestException

# =====================================================
# 1. 프로젝트 경로
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

BOUNDARY_PATH = (
    BASE_DIR
    / "app"
    / "frontend"
    / "public"
    / "gangnam_boundary.geojson"
)

GRAPH_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "walking_network"
    / "gangnam_walk.graphml"
)

# =====================================================
# 2. 다운로드 설정
# =====================================================

# 강남구 경계 주변 완충 거리 (미터)
BUFFER_M = 500

# Overpass API 서버 목록
OVERPASS_SERVERS = [
    "https://overpass.private.coffee/api",
    "https://overpass-api.de/api",
]

# 서버별 최대 시도 횟수
MAX_RETRIES = 3

# 재시도 대기 시간 (초)
RETRY_DELAYS = [15, 30]

# 요청 제한 시간 (초)
REQUEST_TIMEOUT = 180

# OSMnx 설정
ox.settings.use_cache = True
ox.settings.requests_timeout = REQUEST_TIMEOUT

# 서버의 요청 제한 정책 준수
ox.settings.overpass_rate_limit = True


# =====================================================
# 3. 강남구 경계 불러오기
# =====================================================

def load_gangnam_boundary():
    """
    저장된 강남구 GeoJSON 파일을 불러온다.
    """

    if not BOUNDARY_PATH.exists():
        raise FileNotFoundError(
            "강남구 경계 파일이 없습니다.\n"
            "먼저 download_boundary.py를 실행하세요."
        )

    with BOUNDARY_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        boundary_data = json.load(file)

    features = boundary_data.get("features", [])

    if not features:
        raise ValueError(
            "GeoJSON에 강남구 경계 정보가 없습니다."
        )

    geometry_data = features[0]["geometry"]

    polygon = shape(geometry_data)

    if polygon.is_empty or not polygon.is_valid:
        raise ValueError(
            "강남구 경계 폴리곤이 유효하지 않습니다."
        )

    print("[1] 강남구 경계 불러오기 완료", flush=True)

    return polygon


# =====================================================
# 4. 다운로드 영역 생성
# =====================================================

def create_download_polygon(gangnam_polygon):
    """
    강남구 행정경계 주변에 500m 여유 구간을 추가한다.
    """

    # 위경도 -> 미터 좌표계
    projected_polygon, projected_crs = (
        ox.projection.project_geometry(
            gangnam_polygon,
            crs="EPSG:4326",
            to_crs="EPSG:5179",
        )
    )

    # 경계 주변 완충 영역
    buffered_polygon = projected_polygon.buffer(
        BUFFER_M
    )

    # 미터 좌표계 -> 위경도
    download_polygon, _ = (
        ox.projection.project_geometry(
            buffered_polygon,
            crs=projected_crs,
            to_crs="EPSG:4326",
        )
    )

    print(
        f"[2] 다운로드 영역 생성 완료 "
        f"(경계 주변 {BUFFER_M}m)",
        flush=True,
    )

    return download_polygon


# =====================================================
# 5. 보행 네트워크 다운로드
# =====================================================

def download_walking_graph(polygon):
    """
    Overpass API를 이용해 보행 네트워크 다운로드.

    실패하면 일정 시간 대기 후 재시도하고,
    반복 실패 시 다른 서버를 사용한다.
    """

    last_error = None

    for server_index, server_url in enumerate(
        OVERPASS_SERVERS,
        start=1,
    ):
        # 사용 서버 변경
        ox.settings.overpass_url = server_url

        print()
        print(
            f"[3] Overpass 서버 {server_index}/"
            f"{len(OVERPASS_SERVERS)}",
            flush=True,
        )
        print(f"서버 주소: {server_url}", flush=True)

        for attempt in range(1, MAX_RETRIES + 1):
            print()
            print(
                f"다운로드 시도 "
                f"{attempt}/{MAX_RETRIES}",
                flush=True,
            )

            attempt_start = time.perf_counter()

            try:
                graph = ox.graph_from_polygon(
                    polygon,
                    network_type="walk",
                    simplify=True,
                    retain_all=False,
                    truncate_by_edge=True,
                )

                elapsed = (
                    time.perf_counter() - attempt_start
                )

                if len(graph.nodes) == 0:
                    raise ValueError(
                        "다운로드된 보행 노드가 없습니다."
                    )

                print()
                print("보행 네트워크 다운로드 성공!")
                print(
                    f"다운로드 소요 시간: {elapsed:.1f}초"
                )
                print(
                    f"노드: {len(graph.nodes):,}개"
                )
                print(
                    f"링크: {len(graph.edges):,}개"
                )

                return graph

            except (
                RequestException,
                ox._errors.ResponseStatusCodeError,
                ox._errors.InsufficientResponseError,
            ) as error:
                last_error = error

                elapsed = (
                    time.perf_counter() - attempt_start
                )

                print()
                print(
                    f"다운로드 실패 ({elapsed:.1f}초 경과)",
                    flush=True,
                )
                print(
                    f"오류 유형: {type(error).__name__}",
                    flush=True,
                )
                print(
                    "외부 서버의 응답 또는 요청 처리에 "
                    "문제가 발생했습니다.",
                    flush=True,
                )

                # 마지막 시도가 아니라면 대기 후 재시도
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt - 1]

                    print(
                        f"{delay}초 후 재시도합니다.",
                        flush=True,
                    )

                    time.sleep(delay)

        print()
        print(
            "현재 서버에서 다운로드하지 못했습니다.",
            flush=True,
        )

        if server_index < len(OVERPASS_SERVERS):
            print(
                "다른 Overpass 서버로 전환합니다.",
                flush=True,
            )

    raise RuntimeError(
        "모든 Overpass 서버에서 다운로드에 "
        "실패했습니다. 잠시 후 다시 실행하거나 "
        "네트워크 연결을 확인하세요."
    ) from last_error


# =====================================================
# 6. 네트워크 파일 저장
# =====================================================

def save_walking_graph(graph):
    """
    다운로드 완료된 보행 네트워크를 GraphML로 저장한다.
    """

    GRAPH_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("[4] GraphML 파일 저장 중...", flush=True)

    ox.save_graphml(
        graph,
        filepath=GRAPH_PATH,
    )

    print("GraphML 파일 저장 완료!")
    print(f"저장 경로: {GRAPH_PATH}")
    print(
        f"파일 크기: "
        f"{GRAPH_PATH.stat().st_size / 1024 / 1024:.2f} MB"
    )


# =====================================================
# 7. 전체 실행
# =====================================================

def main():
    print("=" * 55)
    print("강남구 보행 네트워크 구축")
    print("=" * 55)

    total_start = time.perf_counter()

    # 이미 다운로드된 경우 재사용
    if GRAPH_PATH.exists():
        print()
        print("이미 저장된 보행 네트워크가 있습니다.")
        print(f"파일: {GRAPH_PATH}")
        print("다운로드를 생략합니다.")
        return

    # 강남구 경계 불러오기
    gangnam_polygon = load_gangnam_boundary()

    # 다운로드 영역 생성
    download_polygon = create_download_polygon(
        gangnam_polygon
    )

    # 보행 네트워크 다운로드
    graph = download_walking_graph(
        download_polygon
    )

    # GraphML 저장
    save_walking_graph(graph)

    total_elapsed = (
        time.perf_counter() - total_start
    )

    print()
    print("=" * 55)
    print("강남구 보행 네트워크 구축 완료")
    print(f"전체 소요 시간: {total_elapsed:.1f}초")
    print("=" * 55)


if __name__ == "__main__":
    main()
