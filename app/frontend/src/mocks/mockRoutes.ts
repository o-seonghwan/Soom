
import type {
  Coordinate,
  RouteRequest,
  RouteResponse,
} from "../types/route";

// 두 좌표 사이의 직선거리 계산 (미터)
function distanceM(
  a: Coordinate,
  b: Coordinate
): number {
  const rad = Math.PI / 180;

  const lat1 = a[0] * rad;
  const lat2 = b[0] * rad;

  const dLat = (b[0] - a[0]) * rad;
  const dLng = (b[1] - a[1]) * rad;

  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(dLng / 2) ** 2;

  return 6371000 * 2 * Math.asin(Math.sqrt(h));
}

// 가상 경로 생성
export function getMockRoutes(
  request: RouteRequest
): RouteResponse {
  const { start, end, avoidanceLevel } = request;

  // 회피 강도에 따른 우회 정도
  const factor = 0.15 + 0.45 * Math.max(0, Math.min(100, avoidanceLevel)) / 100;

  // 두 좌표의 차이
  const dLat = end[0] - start[0];
  const dLng = end[1] - start[1];

  // 중간 지점
  const midLat = (start[0] + end[0]) / 2;
  const midLng = (start[1] + end[1]) / 2;

  // 우회 경유지 생성
  const waypoint: Coordinate = [
    midLat - dLng * factor,
    midLng + dLat * factor,
  ];

  // 경로별 거리 계산
  const directDistance = distanceM(start, end);

  const detourDistance =
    distanceM(start, waypoint) +
    distanceM(waypoint, end);

  return {
    routes: [
      {
        id: "shortest",
        name: "최단 경로 (예시)",
        distanceM: Math.round(directDistance),
        coordinates: [start, end],
      },
      {
        id: "safest",
        name: "위험 회피 경로 (예시)",
        distanceM: Math.round(detourDistance),
        coordinates: [start, waypoint, end],
      },
    ],
  };
}
