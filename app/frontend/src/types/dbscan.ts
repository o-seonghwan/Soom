export interface DbscanCluster {
  id: string;
  lat: number;
  lng: number;
  representativePlace: string;
  recordCount: number;
  placeCount: number | null;
  verdict: string;
  repeatedYears: string;
}

export interface DbscanCandidate {
  id: string;
  clusterId: string;
  rank: number;
  lat: number;
  lng: number;
  nodeId: string;
  representativePlace: string;
  walkingDistanceM: number;
  recommendedType: string;
  exposureChange: string;
  riskProbabilityOOF: number | null;
  pedestrianFlowPercentile: number | null;
  fieldCheck: string;
}

export interface DbscanSitesResponse {
  source: "dbscan-analysis-csv";
  parameters: {
    epsM: number;
    minRecords: number;
    accessLimitM: number;
    maxCandidatesPerCluster: number;
    origin: string;
  };
  summary: {
    clusterCount: number;
    candidateCount: number;
    reviewClusterCount: number;
  };
  clusters: DbscanCluster[];
  candidates: DbscanCandidate[];
  disclaimer: string;
}
