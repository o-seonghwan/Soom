export function getRiskColor(score: number): string {
  if (score >= 80) return "#dc2626"; // 빨강
  if (score >= 60) return "#f97316"; // 주황
  if (score >= 40) return "#eab308"; // 노랑
  if (score >= 20) return "#84cc16"; // 연두
  return "#16a34a";                  // 초록
}