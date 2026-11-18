export interface CleanEdgeFeature {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: [number, number][] };
  properties: {
    edgeId: string;
    score: number | null;
    cleanIndex: number | null;
  };
}

export interface CleanEdgeCollection {
  type: "FeatureCollection";
  source: "model-csv" | "mock";
  features: CleanEdgeFeature[];
}
