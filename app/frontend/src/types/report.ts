
import type { Coordinate } from "./route";

// 사용자가 입력하는 제보 유형
export type ReportType =
  | "smoking"
  | "cigarette_butt"
  | "other";

// 제보 등록 요청
export interface ReportRequest {
  location: Coordinate;
  type: ReportType;
  observedAt: string;
  description: string;
}

// 저장된 제보
export interface Report extends ReportRequest {
  id: string;
  createdAt: string;
  status: "pending" | "verified" | "rejected";
}
