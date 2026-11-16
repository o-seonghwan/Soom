export interface RiskLocation {
  id: string;
  lat: number;
  lng: number;
  score: number; // 0~100
  radiusM: number; // 지도에 표시할 반경(m)
}