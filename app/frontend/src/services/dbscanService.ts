import type { DbscanSitesResponse } from "../types/dbscan";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getDbscanSites(authHeader: string): Promise<DbscanSitesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/b2g/dbscan/sites`, {
    headers: { Authorization: authHeader },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = "분석 결과 CSV를 확인하세요.";
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the default if the backend returns a non-JSON response.
    }
    throw new Error(`DBSCAN 입지 후보를 불러올 수 없습니다 (${response.status}): ${detail}`);
  }
  const payload: unknown = await response.json();
  if (!payload || typeof payload !== "object" || !("source" in payload) ||
      payload.source !== "dbscan-analysis-csv" || !("clusters" in payload) ||
      !Array.isArray(payload.clusters) || !("candidates" in payload) ||
      !Array.isArray(payload.candidates)) {
    throw new Error("DBSCAN 입지 후보 데이터 형식이 올바르지 않습니다.");
  }
  return payload as DbscanSitesResponse;
}
