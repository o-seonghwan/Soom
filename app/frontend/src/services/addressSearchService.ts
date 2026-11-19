import type { Coordinate } from "../types/route";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface AddressSuggestion {
  id: string;
  title: string;
  address: string;
  lat: number;
  lng: number;
  kind: string;
}

async function checkResponse(response: Response): Promise<void> {
  if (response.ok) return;
  let detail = `주소 검색 오류 (${response.status})`;
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
      detail = data.detail;
    }
  } catch { /* fallback */ }
  throw new Error(detail);
}

export async function suggestAddresses(query: string, signal?: AbortSignal): Promise<AddressSuggestion[]> {
  const url = new URL(`${API_BASE_URL}/api/search-addresses`);
  url.searchParams.set("q", query);
  const response = await fetch(url.toString(), { signal, cache: "no-store" });
  await checkResponse(response);
  const data: unknown = await response.json();
  if (!data || typeof data !== "object" || !("suggestions" in data) || !Array.isArray(data.suggestions)) {
    throw new Error("주소 검색 응답 형식이 올바르지 않습니다.");
  }
  return data.suggestions as AddressSuggestion[];
}

export async function geocodeAddress(query: string, signal?: AbortSignal): Promise<Coordinate> {
  const url = new URL(`${API_BASE_URL}/api/geocode-address`);
  url.searchParams.set("q", query);
  const response = await fetch(url.toString(), { signal, cache: "no-store" });
  await checkResponse(response);
  const data: unknown = await response.json();
  if (!data || typeof data !== "object" || !("lat" in data) || !("lng" in data) ||
      typeof data.lat !== "number" || typeof data.lng !== "number") {
    throw new Error("주소 좌표 결과 형식이 올바르지 않습니다.");
  }
  return [data.lat, data.lng];
}
