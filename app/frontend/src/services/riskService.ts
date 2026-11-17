
import type { RiskLocation } from "../types/risk";

// =====================================================
// 1. API 서버 설정
// =====================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";


// =====================================================
// 2. 위치별 위험도 조회
// =====================================================

export async function getRisks(): Promise<RiskLocation[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/risks`
  );

  if (!response.ok) {
    throw new Error(
      `위험도 조회 실패: ${response.status}`
    );
  }

  const data: unknown = await response.json();

  if (!Array.isArray(data)) {
    throw new Error(
      "위험도 API 응답 형식이 올바르지 않습니다."
    );
  }

  return data as RiskLocation[];
}
