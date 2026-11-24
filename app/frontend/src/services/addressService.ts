import type { Coordinate } from "../types/route";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Display-only reverse geocoding; never change route snap coordinates. */
export async function lookupAddress(point: Coordinate, signal?: AbortSignal): Promise<string | null> {
  const url = new URL(`${API_BASE}/api/reverse-address`, window.location.origin);
  url.searchParams.set("lat", String(point[0]));
  url.searchParams.set("lng", String(point[1]));
  const response = await fetch(url.toString(), { signal });
  if (!response.ok) throw new Error(`주소 조회 오류 ${response.status}`);
  const data: unknown = await response.json();
  if (data && typeof data === "object" && "source" in data && data.source === "unconfigured") {
    throw new Error("주소 변환을 사용하려면 백엔드 Railway에 VWORLD_API_KEY를 설정해야 합니다.");
  }
  if (data && typeof data === "object" && "address" in data) {
    const address = (data as { address: unknown }).address;
    return typeof address === "string" && address.trim() ? address : null;
  }
  return null;
}
