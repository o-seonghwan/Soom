
import type {
  Report,
  ReportRequest,
} from "../types/report";

import {
  getMockReports,
  addMockReport,
} from "../mocks/mockReports";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";

const USE_MOCK =
  import.meta.env.VITE_USE_MOCK !== "false";

// 제보 목록 조회
export async function getReports(): Promise<Report[]> {
  if (USE_MOCK) {
    return getMockReports();
  }

  const response = await fetch(`${API_BASE_URL}/api/reports`);

  if (!response.ok) {
    throw new Error(`제보 조회 실패: ${response.status}`);
  }

  return (await response.json()) as Report[];
}

// 제보 등록
export async function createReport(
  request: ReportRequest
): Promise<Report> {
  if (USE_MOCK) {
    return addMockReport(request);
  }

  const response = await fetch(`${API_BASE_URL}/api/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`제보 등록 실패: ${response.status}`);
  }

  return (await response.json()) as Report;
}
