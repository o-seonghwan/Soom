
import type {
  Report,
  ReportRequest,
} from "../types/report";

// =====================================================
// 1. FastAPI 주소
// =====================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";


// =====================================================
// 2. 제보 목록 조회
// =====================================================

export async function getReports(): Promise<Report[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/reports`
  );

  if (!response.ok) {
    throw new Error(
      `제보 목록 조회에 실패했습니다. (${response.status})`
    );
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error(
      "제보 목록 API 응답 형식이 올바르지 않습니다."
    );
  }

  return data as Report[];
}


// =====================================================
// 3. 신규 제보 등록
// =====================================================

export async function createReport(
  request: ReportRequest
): Promise<Report> {
  const response = await fetch(
    `${API_BASE_URL}/api/reports`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    let message = "제보 등록에 실패했습니다.";

    try {
      const errorData: unknown =
        await response.json();

      if (
        typeof errorData === "object" &&
        errorData !== null &&
        "detail" in errorData &&
        typeof errorData.detail === "string"
      ) {
        message = errorData.detail;
      }
    } catch {
      // JSON 형태가 아니라면 기본 오류 메시지 사용
    }

    throw new Error(message);
  }

  const data: unknown = await response.json();

  if (
    typeof data !== "object" ||
    data === null ||
    !("id" in data) ||
    typeof data.id !== "string"
  ) {
    throw new Error(
      "제보 등록 API 응답 형식이 올바르지 않습니다."
    );
  }

  return data as Report;
}
