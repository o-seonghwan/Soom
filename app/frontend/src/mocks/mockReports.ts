
import type {
  Report,
  ReportRequest,
} from "../types/report";

// 메모리에 저장되는 임시 제보 목록
const reports: Report[] = [];

export function getMockReports(): Report[] {
  return [...reports];
}

export function addMockReport(
  request: ReportRequest
): Report {
  const report: Report = {
    ...request,
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    status: "pending",
  };

  reports.push(report);

  return report;
}
