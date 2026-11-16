import type { CleanEdgeCollection } from "../types/cleanliness";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getB2GCleanEdges(): Promise<CleanEdgeCollection> {
  const response = await fetch(`${API_BASE_URL}/api/b2g/cleanliness/edges`);
  if (!response.ok) {
    throw new Error(`보행로 청정지수 조회 실패: ${response.status}`);
  }
  const value: unknown = await response.json();
  if (!value || typeof value !== "object" || !("features" in value)) {
    throw new Error("청정지수 응답 형식이 잘못되었습니다.");
  }
  const data = value as CleanEdgeCollection;
  if (data.type !== "FeatureCollection" || !Array.isArray(data.features)
      || !["mock","model-csv"].includes(data.source)) {
    throw new Error("청정지수 GeoJSON 형식이 잘못되었습니다.");
  }
  return data;
}
