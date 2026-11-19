export interface ChildcareExposure {
  id: string;
  name: string;
  type: string;
  address: string;
  enrollment: number;
  lat: number;
  lng: number;
  nearbyPointCount: number;
  nearbyMaxRisk: number | null;
  nearbyMeanRisk: number | null;
  highRiskPointCount: number;
  exposureScore: number;
  priorityRank: number;
}

export interface ChildcareExposureResponse {
  source: "childcare-exposure-csv";
  analysisRadiusM: number;
  summary: { nurseryCount: number; withHighRiskPoints: number };
  nurseries: ChildcareExposure[];
  disclaimer: string;
}
