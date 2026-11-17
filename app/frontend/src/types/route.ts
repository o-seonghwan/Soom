
export type Coordinate = [number, number];

// 경로 탐색 요청
export interface RouteRequest {
  start: Coordinate;
  end: Coordinate;
  avoidanceLevel: number; // Continuous 0–100 avoidance strength
}

// 경로 탐색 결과
export interface Route {
  id: string;
  name: string;

  // 실제 보행 네트워크 경로 거리
  distanceM: number;

  // 예상 보행 시간 (분)
  estimatedMinutes?: number;

  // 지도에 표시할 경로 좌표
  coordinates: Coordinate[];

  // 보행 링크에 연결된 실제 시작·끝 지점
  snappedStart?: Coordinate;
  snappedEnd?: Coordinate;

  // 사용자 클릭 지점에서 보행 링크까지 거리
  startSnapDistanceM?: number;
  endSnapDistanceM?: number;
}

// 경로 API 응답
export interface RouteResponse {
  routes: Route[];
}
