
import type {
  RouteRequest,
  RouteResponse,
} from "../types/route";

// =====================================================
// 1. FastAPI 서버 주소
// =====================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";


// =====================================================
// 2. 일반 경로 + 위험 회피 경로 조회
// =====================================================

export async function getRoutes(
  request: RouteRequest,
  signal?: AbortSignal
): Promise<RouteResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/routes`,
    {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    let message = "경로 탐색에 실패했습니다.";

    try {
      const errorData: unknown = await response.json();

      if (
        typeof errorData === "object" &&
        errorData !== null &&
        "detail" in errorData &&
        typeof errorData.detail === "string"
      ) {
        message = errorData.detail;
      }
    } catch {
      // JSON이 아닌 오류 응답은 기본 메시지 사용
    }

    throw new Error(message);
  }

  const data: unknown = await response.json();

  if (
    typeof data !== "object" ||
    data === null ||
    !("routes" in data) ||
    !Array.isArray(data.routes)
  ) {
    throw new Error(
      "경로 API 응답 형식이 올바르지 않습니다."
    );
  }

  return data as RouteResponse;
}
