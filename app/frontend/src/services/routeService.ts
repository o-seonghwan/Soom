
import type {
  RouteRequest,
  RouteResponse,
} from "../types/route";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";

// 실제 A* 기반 일반 최단 도보 경로 조회
export async function getRoutes(
  request: RouteRequest
): Promise<RouteResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/routes/shortest`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    let message = "경로 탐색에 실패했습니다.";

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      }
    } catch {
      // 오류 응답이 JSON이 아닌 경우 기본 메시지 사용
    }

    throw new Error(message);
  }

  return (await response.json()) as RouteResponse;
}
