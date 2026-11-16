/** B2G-only map legend. High cleanliness is green; low is red. */
export function getCleanColor(index: number): string {
  if (index >= 80) return "#16803c";
  if (index >= 60) return "#84cc16";
  if (index >= 40) return "#eab308";
  if (index >= 20) return "#f97316";
  return "#dc2626";
}
