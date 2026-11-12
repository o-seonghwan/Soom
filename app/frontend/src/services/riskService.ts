
import type { RiskLocation } from "../types/risk";
import { mockRisks } from "../mocks/mockRisks";

// 추후 FastAPI 서버 주소
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// 개발 단계에서는 Mock 데이터 사용
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

export async function getRisks(): Promise<RiskLocation[]> {
  if (USE_MOCK) {
    return mockRisks;
  }

  const response = await fetch(`${API_BASE_URL}/api/risks`);

  if (!response.ok) {
    throw new Error(`위험도 조회 실패: ${response.status}`);
  }

  return (await response.json()) as RiskLocation[];
}
