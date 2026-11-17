
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

# 강남역 주변 기존 테스트 좌표
START = [37.4979, 127.0276]
END = [37.5000, 127.0300]

TIMEOUT_SECONDS = 120

results = []


def request_api(method, path, payload=None):
    url = BASE_URL + path
    body = None

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            status = response.status
            content = response.read()

    except urllib.error.HTTPError as error:
        status = error.code
        content = error.read()

    elapsed = time.perf_counter() - started

    try:
        data = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        data = {
            "raw": content.decode(
                "utf-8",
                errors="replace",
            )[:500],
        }

    return status, data, elapsed


def record(name, passed, detail=""):
    label = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))

    print(f"[{label}] {name}")

    if detail:
        print(f"       {detail}")


def validate_route(route):
    if not isinstance(route, dict):
        return False

    if not isinstance(route.get("distanceM"), (int, float)):
        return False

    if route["distanceM"] < 0:
        return False

    coordinates = route.get("coordinates")

    if not isinstance(coordinates, list):
        return False

    if len(coordinates) < 1:
        return False

    for point in coordinates:
        if not isinstance(point, list) or len(point) != 2:
            return False

        lat, lon = point

        if not all(
            isinstance(value, (int, float))
            and math.isfinite(value)
            for value in point
        ):
            return False

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return False

    return True


def test_health():
    status, data, elapsed = request_api(
        "GET",
        "/api/health",
    )

    passed = (
        status == 200
        and isinstance(data, dict)
        and data.get("graph_loaded") is True
    )

    record(
        "보행 네트워크 및 서버 상태",
        passed,
        f"HTTP {status}, {elapsed:.2f}초",
    )


def test_risks():
    status, data, elapsed = request_api(
        "GET",
        "/api/risks",
    )

    passed = (
        status == 200
        and isinstance(data, list)
        and all(
            isinstance(item, dict)
            and "score" in item
            and "lat" in item
            and "lng" in item
            for item in data
        )
    )

    record(
        "위치별 위험도 API",
        passed,
        f"HTTP {status}, {elapsed:.2f}초",
    )


def test_edge_risks():
    status, data, elapsed = request_api(
        "GET",
        "/api/risks/edges?limit=10",
    )

    summary = (
        data.get("summary", {})
        if isinstance(data, dict)
        else {}
    )

    affected = summary.get("affectedEdges")

    passed = (
        status == 200
        and isinstance(affected, int)
        and affected > 0
        and isinstance(data.get("edges"), list)
    )

    record(
        "위험도와 보행 링크 연결",
        passed,
        (
            f"HTTP {status}, "
            f"위험 영향 링크 {affected}개, "
            f"{elapsed:.2f}초"
        ),
    )


def test_shortest_route():
    status, data, elapsed = request_api(
        "POST",
        "/api/routes/shortest",
        {
            "start": START,
            "end": END,
            "avoidanceLevel": "medium",
        },
    )

    routes = (
        data.get("routes", [])
        if isinstance(data, dict)
        else []
    )

    passed = (
        status == 200
        and len(routes) == 1
        and routes[0].get("id") == "shortest"
        and validate_route(routes[0])
    )

    record(
        "일반 A* 최단경로",
        passed,
        f"HTTP {status}, {elapsed:.2f}초",
    )


def test_comparison(level):
    status, data, elapsed = request_api(
        "POST",
        "/api/routes",
        {
            "start": START,
            "end": END,
            "avoidanceLevel": level,
        },
    )

    routes = (
        data.get("routes", [])
        if isinstance(data, dict)
        else []
    )

    ids = {
        route.get("id")
        for route in routes
        if isinstance(route, dict)
    }

    passed = (
        status == 200
        and len(routes) == 2
        and ids == {"shortest", "safest"}
        and all(validate_route(route) for route in routes)
    )

    record(
        f"일반·위험 회피 A* 비교 ({level})",
        passed,
        f"HTTP {status}, {elapsed:.2f}초",
    )

    if passed:
        shortest = next(
            r for r in routes if r["id"] == "shortest"
        )
        safest = next(
            r for r in routes if r["id"] == "safest"
        )

        print(
            f"       일반 거리: "
            f"{shortest['distanceM']}m"
        )
        print(
            f"       회피 거리: "
            f"{safest['distanceM']}m"
        )

        same_path = (
            shortest["coordinates"] == safest["coordinates"]
        )
        print(
            f"       경로 좌표 동일: {same_path}"
        )

    return data if passed else None


def test_public_reports():
    status, data, elapsed = request_api(
        "GET",
        "/api/reports",
    )

    passed = status == 200 and isinstance(data, list)

    record(
        "공개 제보 조회",
        passed,
        f"HTTP {status}, {elapsed:.2f}초",
    )

    if passed:
        all_verified = all(
            report.get("status") == "verified"
            for report in data
        )

        record(
            "공개 제보 승인 상태 확인",
            all_verified,
            f"조회 제보 수: {len(data)}건",
        )


def test_admin_security():
    # 인증 헤더 없이 요청
    for path in (
        "/api/admin/me",
        "/api/admin/reports",
    ):
        status, data, elapsed = request_api(
            "GET",
            path,
        )

        record(
            f"관리자 인증 보호: {path}",
            status == 401,
            f"HTTP {status}, {elapsed:.2f}초",
        )


def main():
    print("=" * 55)
    print("17단계 강남구 서비스 통합 API 검사")
    print("=" * 55)
    print("기존 DB 데이터는 변경하지 않습니다.")

    tests = [
        ("서버 상태", test_health),
        ("위험도 API", test_risks),
        ("링크 위험도", test_edge_risks),
        ("일반 A*", test_shortest_route),
        ("회피 A* 낮음", lambda: test_comparison("low")),
        ("회피 A* 높음", lambda: test_comparison("high")),
        ("공개 제보", test_public_reports),
        ("관리자 보호", test_admin_security),
    ]

    for name, func in tests:
        print()
        print(f"--- {name} ---")

        try:
            func()
        except Exception as error:
            record(
                name,
                False,
                f"{type(error).__name__}: {error}",
            )

    passed_count = sum(
        1 for _, passed, _ in results if passed
    )
    total_count = len(results)

    print()
    print("=" * 55)
    print(
        f"테스트 결과: {passed_count}/{total_count} 통과"
    )
    print("=" * 55)

    if passed_count != total_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
