import type { ChildcareExposureResponse } from "../types/childcare";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getChildcareExposure(authHeader: string): Promise<ChildcareExposureResponse> {
  const response = await fetch(`${API_BASE_URL}/api/b2g/childcare/exposure`, {
    headers: { Authorization: authHeader },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = "어린이집 노출순위 CSV를 확인하세요.";
    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch { /* use the default */ }
    throw new Error(`어린이집 보호 순위 로딩 실패 (${response.status}): ${message}`);
  }
  const data: unknown = await response.json();
  if (!data || typeof data !== "object" || !("source" in data) ||
      data.source !== "childcare-exposure-csv" || !("nurseries" in data) ||
      !Array.isArray(data.nurseries)) {
    throw new Error("어린이집 보호 순위 응답 형식이 올바르지 않습니다.");
  }
  return data as ChildcareExposureResponse;
}
