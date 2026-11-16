import type { CleanEdgeFeature } from "../types/cleanliness";

/**
 * A walking road may exist as forward/reverse directed links.
 * Drawing both with alpha makes an 18%-opaque line appear ~33%-opaque.
 * Only the B2C visualization uses this de-duplication; routing data,
 * directional graph edges and the B2G view remain untouched.
 */
export function deduplicateCleanEdges(
  features: CleanEdgeFeature[],
): CleanEdgeFeature[] {
  const unique = new Map<string, CleanEdgeFeature>();

  for (const feature of features) {
    const coordinates = feature.geometry.coordinates;
    // 6 digits ~= 0.1m: retain separately drawn parallel streets.
    const points = coordinates.map(([lng, lat]) =>
      `${lng.toFixed(6)},${lat.toFixed(6)}`,
    );
    const forward = points.join("|");
    const reverse = [...points].reverse().join("|");
    const key = forward < reverse ? forward : reverse;
    const current = unique.get(key);

    if (!current) {
      unique.set(key, feature);
    } else if (feature.properties.cleanIndex < current.properties.cleanIndex) {
      // A physical street uses the more conservative (lower) clean index.
      unique.set(key, feature);
    }
  }

  return Array.from(unique.values());
}
