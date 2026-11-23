
import { Fragment, useEffect, useState } from "react";
import L from "leaflet";

import {
  MapContainer,
  TileLayer,
  ZoomControl,
  CircleMarker,
  Marker,
  Polyline,
  Popup,
  GeoJSON,
  useMap,
  useMapEvents,
} from "react-leaflet";

import type { Feature, FeatureCollection, GeoJsonObject, Polygon } from "geojson";
import type { Coordinate, Route } from "../types/route";
import type { RiskLocation } from "../types/risk";
import type { Report } from "../types/report";

import { getCleanColor } from "../utils/cleanColor";
import type { CleanEdgeFeature } from "../types/cleanliness";
import type { DbscanSitesResponse } from "../types/dbscan";
import type { AddressSuggestion } from "../services/addressSearchService";
import type { ChildcareExposure } from "../types/childcare";
import MapRouteCard from "./MapRouteCard";
import RoutePanel from "./RoutePanel";
import type { RouteRequest } from "../types/route";
import { deduplicateCleanEdges } from "../utils/deduplicateCleanEdges";
import "leaflet/dist/leaflet.css";

// Use the existing transparent smoking-zone PNG directly on the map.
// No enclosing circle, border, or background is added to the marker.
const smokingZoneIcon = L.icon({
  iconUrl: "/icons/smoking-zone.png",
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -17],
});

// 강남구 지도 중심 (초기 임시 위치)
const GANGNAM_CENTER: Coordinate = [
  37.4979,
  127.0470,
];

interface MapViewProps {
  audience?: "b2c" | "b2g";
  start: Coordinate | null;
  end: Coordinate | null;
  routes: Route[];
  selectedRouteId?: "shortest" | "safest";
  fitBoundsRoutes?: Route[];
  risks: RiskLocation[];
  cleanlinessEdges?: CleanEdgeFeature[];
  dbscanSites?: DbscanSitesResponse | null;
  showDbscanSites?: boolean;
  selectedDbscanCluster?: string;
  selectedChildcare?: ChildcareExposure | null;
  reports: Report[];
  showRisks: boolean;
  showReports: boolean;
  avoidanceLevel?: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange?: (value: RouteRequest["avoidanceLevel"]) => void;
  onToggleCleanliness?: () => void;
  onToggleReports?: () => void;
  riskNoticeOpen?: boolean;
  riskNoticeFading?: boolean;
  onToggleRiskNotice?: () => void;
  onCloseRiskNotice?: () => void;
  reportLocation: Coordinate | null;
  focusPoint: Coordinate | null;
  selectionMode?: "start" | "end";
  startAddress?: string | null;
  endAddress?: string | null;
  routeLoading?: boolean;
  onSearch?: () => void;
  onSelectLocation?: (mode: "start" | "end") => void;
  startInputText?: string;
  endInputText?: string;
  onAddressTextChange?: (mode: "start" | "end", text: string) => void;
  onAddressChoose?: (mode: "start" | "end", suggestion: AddressSuggestion) => void;
  onAddressApply?: (mode: "start" | "end") => Promise<void>;
  onSwapLocations?: () => void;
  onLocate?: () => void;
  currentLocation?: Coordinate | null;
  onMapClick: (point: Coordinate) => void;
}

// 지도 클릭 이벤트
function MapClickHandler({
  onMapClick,
}: {
  onMapClick: (point: Coordinate) => void;
}) {
  useMapEvents({
    click(event) {
      onMapClick([
        event.latlng.lat,
        event.latlng.lng,
      ]);
    },
  });

  return null;
}

// B2G sidebar changes the map's available width; Leaflet must recalculate its size.
function ResizeB2GMap() {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    observer.observe(container);
    map.invalidateSize({ pan: false });
    return () => observer.disconnect();
  }, [map]);
  return null;
}

// 특정 위치로 지도 이동
function MapFocus({
  point,
}: {
  point: Coordinate | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!point) return;

    map.flyTo(
      point,
      Math.max(map.getZoom(), 15),
    );
  }, [map, point]);

  return null;
}

// Once routing finishes, fit the complete route bounds rather than the last selected point.
function FitRoutes({ routes }: { routes: Route[] }) {
  const map = useMap();
  useEffect(() => {
    if (routes.length === 0) return;
    const points = routes.flatMap(route => route.coordinates);
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points.map(([lat, lng]) => [lat, lng] as [number, number]));
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.06), {
        animate: true,
        paddingTopLeft: [35, 155],
        paddingBottomRight: [45, 65],
        maxZoom: 17,
      });
    }
  }, [map, routes]);
  return null;
}

// 최초 경계 데이터 로딩 시 강남구 전체 표시
function BoundaryFocus({
  boundary,
}: {
  boundary: GeoJsonObject | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!boundary) return;

    const layer = L.geoJSON(boundary);
    const bounds = layer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [25, 25],
      });
    }
  }, [map, boundary]);

  return null;
}

// 강남구 바깥 영역을 가리는 마스크 생성
function createOutsideMask(
  boundary: GeoJsonObject
): Feature<Polygon> {
  const geojson = L.geoJSON(boundary).toGeoJSON();

  // 강남구 경계 좌표들을 마스크의 구멍으로 사용
  const holes: number[][][] = [];

  const features = geojson.type === "FeatureCollection"
    ? geojson.features
    : geojson.type === "Feature"
      ? [geojson]
      : [];

  for (const feature of features) {
    const geometry = feature.geometry;

    if (!geometry) continue;

    if (geometry.type === "Polygon") {
      holes.push(geometry.coordinates[0]);
    } else if (geometry.type === "MultiPolygon") {
      for (const polygon of geometry.coordinates) {
        holes.push(polygon[0]);
      }
    }
  }

  return {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [
        // 지도를 덮는 외부 사각형 (경도, 위도)
        [
          [-180, -85],
          [180, -85],
          [180, 85],
          [-180, 85],
          [-180, -85],
        ],
        // 강남구 부분은 구멍으로 제외
        ...holes,
      ],
    },
  };
}

const reportLabels: Record<Report["type"], string> = {
  smoking: "흡연 직접 목격",
  cigarette_butt: "담배꽁초 발견",
  other: "기타 흡연 관련 상황",
};

export default function MapView({
  audience = "b2c",
  start,
  end,
  routes,
  selectedRouteId = "safest",
  fitBoundsRoutes = routes,
  cleanlinessEdges,
  dbscanSites = null,
  showDbscanSites = false,
  selectedDbscanCluster = "",
  selectedChildcare = null,
  reports,
  showRisks,
  showReports,
  avoidanceLevel,
  onAvoidanceLevelChange,
  onToggleCleanliness,
  onToggleReports,
  riskNoticeOpen = false,
  riskNoticeFading = false,
  onToggleRiskNotice,
  onCloseRiskNotice,
  reportLocation,
  focusPoint,
  selectionMode = "start",
  routeLoading = false,
  onSearch,
  onSelectLocation,
  startInputText = "",
  endInputText = "",
  onAddressTextChange,
  onAddressChoose,
  onAddressApply,
  onSwapLocations,
  onLocate,
  currentLocation = null,
  onMapClick,
}: MapViewProps) {
  // 실제 강남구 경계 GeoJSON
  const [boundary, setBoundary] =
    useState<GeoJsonObject | null>(null);

  const [showSmokingZones, setShowSmokingZones] = useState(false);
  const [smokingZones, setSmokingZones] = useState<Array<{id:string;name:string;lat:number;lng:number;locationAccuracy?: "verified" | "address-level" | "unspecified";address?:string;source?:string}>>([]);
  const [smokingZonesMessage, setSmokingZonesMessage] = useState("");

  useEffect(() => {
    if (!showSmokingZones) return;
    let active = true;
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    fetch(`${apiBase}/api/smoking-zones`)
      .then(async response => {
        if (!response.ok) {
          let detail = "";
          try {
            const payload: unknown = await response.json();
            if (payload && typeof payload === "object" && "detail" in payload) {
              const value = payload.detail;
              if (typeof value === "string") detail = value;
            }
          } catch {
            // The backend may return a non-JSON error response.
          }
          throw new Error(detail
            ? `흡연구역 데이터 오류 (${response.status}): ${detail}`
            : `흡연구역 API 요청 실패 (${response.status}). 백엔드 로그 및 LUNG_SMOKING_ZONES_CSV 설정을 확인하세요.`);
        }
        return await response.json() as {source: string; zones: Array<{id:string;name:string;lat:number;lng:number;locationAccuracy?: "verified" | "address-level" | "unspecified";address?:string;source?:string}>};
      })
      .then(result => {
        if (!active) return;
        setSmokingZones(result.zones);
        setSmokingZonesMessage(result.source === "not-configured"
          ? "흡연구역 위치 자료가 아직 연결되지 않았습니다."
          : result.zones.length === 0 ? "연결된 흡연구역 자료에 표시할 위치가 없습니다." : "");
      })
      .catch(error => {
        if (!active) return;
        setSmokingZones([]);
        setSmokingZonesMessage(error instanceof Error ? error.message : "흡연구역 조회 실패");
      });
    return () => { active = false; };
  }, [showSmokingZones]);

  // 최초 한 번 경계 파일 읽기
  useEffect(() => {
    let cancelled = false;

    async function loadBoundary() {
      try {
        const response = await fetch(
          "/gangnam_boundary.geojson"
        );

        if (!response.ok) {
          throw new Error(
            "강남구 경계 파일을 불러올 수 없습니다."
          );
        }

        const data =
          (await response.json()) as GeoJsonObject;

        if (!cancelled) {
          setBoundary(data);
        }
      } catch (error) {
        if (!cancelled) console.error("강남구 경계 데이터 조회 실패:", error);
      }
    }

    void loadBoundary();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="relative h-full w-full">
      <MapContainer
        className="lung-map"
        center={GANGNAM_CENTER}
        zoom={13}
        zoomControl={false}
        style={{
          width: "100%",
          height: "100%",
        }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          url={`https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${import.meta.env.VITE_CARTO_API_KEY}`}
          maxZoom={20}
        />

        <ZoomControl position="bottomright" />
        {audience === "b2g" && <ResizeB2GMap />}

        {/* 지도 입력 및 이동 */}
        <MapClickHandler onMapClick={onMapClick} />
        <MapFocus point={focusPoint} />
        <FitRoutes routes={fitBoundsRoutes} />

        {/* 강남구 전체가 보이도록 초기 조정 */}
        <BoundaryFocus boundary={boundary} />

        {/* 강남구 행정경계 */}
        {/* 강남구 외부 블라인드 마스크 */}
        {boundary && (
          <GeoJSON
            data={createOutsideMask(boundary)}
            interactive={false}
            style={{
              stroke: false,
              fillColor: "#64748b",
              fillOpacity: 0.3,
              fillRule: "evenodd",
            }}
          />
        )}

        {/* B2G: 기존 반투명 다색 보행로 유지 */}
        {audience === "b2g" && showRisks && cleanlinessEdges && cleanlinessEdges.length > 0 && (
          <GeoJSON
            key={`clean-roads-b2g-${cleanlinessEdges.length}`}
            data={{ type: "FeatureCollection", features: deduplicateCleanEdges(cleanlinessEdges) } as FeatureCollection}
            style={(feature) => {
              const rawClean = feature?.properties?.cleanIndex;
              const hasScore = rawClean != null && Number.isFinite(Number(rawClean));
              return {
                color: hasScore ? getCleanColor(Number(rawClean)) : "#64748b",
                weight: 3,
                opacity: 0.36,
                lineCap: "round",
                lineJoin: "round",
              };
            }}
            onEachFeature={(feature, layer) => {
              const rawClean = feature.properties?.cleanIndex;
              const rawRisk = feature.properties?.score;
              if (rawClean == null || !Number.isFinite(Number(rawClean))) {
                layer.bindPopup("보행 링크 청정지수: 데이터 없음 · 회색은 미측정 구간");
              } else {
                const clean = Number(rawClean);
                const risk = rawRisk == null ? null : Number(rawRisk);
                layer.bindPopup(`보행 링크 청정지수: ${clean.toFixed(1)}/100<br/>유효 위험점수: ${risk != null && Number.isFinite(risk) ? risk.toFixed(1) + "/100" : "데이터 없음"}`);
              }
            }}
          />
        )}

        {/* Draw only the two searched routes: inactive first, selected on top.
            B2G keeps the original non-B2C map layers untouched. */}
        {audience === "b2c" ? (
          <>
            {routes.filter(route => route.id !== selectedRouteId).map(route => (
              <Polyline key={`inactive-${route.id}`} positions={route.coordinates}
                bubblingMouseEvents={false}
                pathOptions={{
                  color: "#94a3b8",
                  weight: 5,
                  opacity: 0.75,
                  lineCap: "round",
                  lineJoin: "round",
                }}>
                <Popup><strong>{route.name}</strong><div>선택되지 않은 경로 · {route.distanceM}m</div></Popup>
              </Polyline>
            ))}
            {routes.filter(route => route.id === selectedRouteId).map(route => (
              <Fragment key={`active-${route.id}`}>
                {/* Missing model coverage stays gray; no guessed cleanliness score. */}
                {route.segments && route.segments.length > 0
                  ? route.segments.filter(segment => segment.coordinates.length >= 2).map((segment, index) => (
                    <Polyline key={index} positions={segment.coordinates}
                      bubblingMouseEvents={false}
                      pathOptions={{
                        color: showRisks && segment.cleanIndex != null && Number.isFinite(segment.cleanIndex)
                          ? getCleanColor(segment.cleanIndex)
                          : "#64748b",
                        weight: 7,
                        opacity: 0.98,
                        lineCap: "round",
                        lineJoin: "round",
                      }}>
                      <Popup>
                        <strong>{route.name}</strong>
                        <div>{segment.cleanIndex == null ? "청정지수 데이터 없음" : `보행 링크 청정지수: ${segment.cleanIndex.toFixed(1)}/100`}</div>
                      </Popup>
                    </Polyline>
                  ))
                  : <Polyline positions={route.coordinates} bubblingMouseEvents={false}
                      pathOptions={{ color: "#64748b", weight: 7, opacity: 0.98, lineCap: "round" }}>
                      <Popup><strong>{route.name}</strong><div>보행 링크 청정지수 데이터 없음</div></Popup>
                    </Polyline>}
              </Fragment>
            ))}
          </>
        ) : routes.map(route => (
          <Polyline key={route.id} positions={route.coordinates}
            bubblingMouseEvents={false}
            pathOptions={{
              color: route.id === "shortest" ? "#343A40" : "#72EFDD",
              weight: route.id === "shortest" ? 5 : 6,
              opacity: 0.98,
              lineCap: "round",
              lineJoin: "round",
            }}>
            <Popup><strong>{route.name}</strong><div>거리: {route.distanceM}m</div></Popup>
          </Polyline>
        ))}

        {/* Match the exact outline colors and white centers in the route entry card. */}
        {start && (
          <CircleMarker center={start} radius={audience === "b2c" ? 4.5 : 9} bubblingMouseEvents={false}
            pathOptions={audience === "b2c"
              ? { color: "#3b82f6", weight: 3, fillColor: "#ffffff", fillOpacity: 1 }
              : { color: "#15803d", weight: 3, fillColor: "#22c55e", fillOpacity: 1 }}>
            <Popup>출발지</Popup>
          </CircleMarker>
        )}
        {end && (
          <CircleMarker center={end} radius={audience === "b2c" ? 4.5 : 9} bubblingMouseEvents={false}
            pathOptions={audience === "b2c"
              ? { color: "#72EFDD", weight: 3, fillColor: "#ffffff", fillOpacity: 1 }
              : { color: "#b91c1c", weight: 3, fillColor: "#ef4444", fillOpacity: 1 }}>
            <Popup>목적지</Popup>
          </CircleMarker>
        )}
        {audience === "b2c" && currentLocation && (
          <CircleMarker center={currentLocation} radius={4} bubblingMouseEvents={false}
            pathOptions={{ color: "#ffffff", weight: 1, fillColor: "#111111", fillOpacity: 1 }}
          >
            <Popup>현재 위치</Popup>
          </CircleMarker>
        )}

        {/* Publicly documented smoking facilities only (no no-smoking data). */}
        {showSmokingZones && smokingZones.map(zone => (
          <Marker key={zone.id} position={[zone.lat, zone.lng]} icon={smokingZoneIcon}
            bubblingMouseEvents={false} title={zone.name}>
            <Popup>
              <strong>{zone.name}</strong>
              <div>{zone.address || "주소 정보 없음"}</div>
              <div>{zone.locationAccuracy === "verified" ? "현장 위치 검증됨" : zone.locationAccuracy === "address-level" ? "주소 기반 추정 위치 · 실제 흡연시설 위치와 다를 수 있음" : "위치 검증 여부 미확인"}</div>
              {zone.source && <div>출처: {zone.source}</div>}
            </Popup>
          </Marker>
        ))}

        {/* Administrator-only DBSCAN candidate locations; no cluster-center circles. */}
        {audience === "b2g" && showDbscanSites && dbscanSites && (
          <>
            {dbscanSites.candidates.filter(candidate =>
              !selectedDbscanCluster || candidate.clusterId === selectedDbscanCluster
            ).map(candidate => (
              <CircleMarker key={`site-${candidate.id}`}
                center={[candidate.lat, candidate.lng]} radius={8} bubblingMouseEvents={false}
                pathOptions={{
                  color: "#065f46", weight: 3,
                  fillColor: "#2dd4bf", fillOpacity: 0.95,
                }}>
                <Popup>
                  <strong>흡연시설 입지 후보</strong>
                  <div>적발 집중지: {candidate.representativePlace}</div>
                  <div>적발 집중지 주변 {Math.round(candidate.walkingDistanceM)}m</div>
                  <div>현장 검토 전 분석 후보 · 실제 설치 시설 아님</div>
                </Popup>
              </CircleMarker>
            ))}
          </>
        )}

        {/* Selected childcare facility: show a distinct marker when reviewing priority ranking. */}
        {audience === "b2g" && selectedChildcare && (
          <CircleMarker
            center={[selectedChildcare.lat, selectedChildcare.lng]}
            radius={10}
            bubblingMouseEvents={false}
            pathOptions={{ color: "#5b21b6", weight: 3, fillColor: "#c4b5fd", fillOpacity: 0.95 }}>
            <Popup>
              <strong>{selectedChildcare.name}</strong>
              <div>어린이집 보호 우선순위 {selectedChildcare.priorityRank}위</div>
              <div>주변 노출점수 {selectedChildcare.exposureScore.toFixed(1)}</div>
              <div>주변 AI 위험지수 기반 · 실측 흡연 노출 아님</div>
            </Popup>
          </CircleMarker>
        )}

        {/* 사용자 제보 */}
        {showReports &&
          reports.map((report) => (
            <CircleMarker
              key={report.id}
              center={report.location}
              radius={7}
              bubblingMouseEvents={false}
              pathOptions={{
                color: audience === "b2g"
                  ? report.status === "pending" ? "#b45309" : report.status === "verified" ? "#15803d" : "#475569"
                  : "#7e22ce",
                fillColor: audience === "b2g"
                  ? report.status === "pending" ? "#fbbf24" : report.status === "verified" ? "#22c55e" : "#94a3b8"
                  : "#a855f7",
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Popup>
                <strong>
                  {reportLabels[report.type]}
                </strong>

                {audience === "b2g" && (
                  <div>
                    신고 상태: {report.status === "pending" ? "검토 대기" : report.status === "verified" ? "승인" : "반려"}
                  </div>
                )}
                <div>
                  목격 시간:{" "}
                  {new Date(
                    report.observedAt
                  ).toLocaleString("ko-KR")}
                </div>

                <div>
                  상태:{" "}
                  {report.status === "pending"
                    ? "검토 대기"
                    : report.status === "verified"
                      ? "확인"
                      : "반려"}
                </div>

                {report.description && (
                  <div>{report.description}</div>
                )}
              </Popup>
            </CircleMarker>
          ))}

        {/* 작성 중인 제보 위치 */}
        {reportLocation && (
          <CircleMarker
            center={reportLocation}
            radius={11}
            bubblingMouseEvents={false}
            pathOptions={{
              color: "#581c87",
              fillColor: "#c084fc",
              fillOpacity: 0.7,
              weight: 3,
              dashArray: "4 4",
            }}
          >
            <Popup>
              선택한 제보 위치 (등록 전)
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>

      {audience === "b2c" && onSelectLocation && onSwapLocations && onSearch && onAddressTextChange && onAddressChoose && onAddressApply && (
        <div className="pointer-events-none absolute left-3 top-3 z-[800] w-[min(440px,calc(100%-5.5rem))]">
          <MapRouteCard start={start} end={end} selectionMode={selectionMode}
            startText={startInputText} endText={endInputText} loading={routeLoading}
            onMapSelect={onSelectLocation} onTextChange={onAddressTextChange}
            onChoose={onAddressChoose} onApplyText={onAddressApply}
            onSwap={onSwapLocations} onSearch={onSearch} />
        </div>
      )}

      <div className={`absolute right-3 top-3 z-[650] flex items-start gap-2 ${audience === "b2c" ? "max-[760px]:top-[132px]" : ""}`}>
        {audience === "b2c" && avoidanceLevel !== undefined && onAvoidanceLevelChange && (
          <div className="w-[min(220px,calc(100vw-5.5rem))]">
            <RoutePanel avoidanceLevel={avoidanceLevel} onAvoidanceLevelChange={onAvoidanceLevelChange} />
          </div>
        )}
        <div className="flex flex-col items-end gap-2">
        <button type="button" onClick={onToggleCleanliness}
          aria-label={showRisks ? "보행로 청정지수 숨기기" : "보행로 청정지수 표시"}
          aria-pressed={showRisks} title="보행로 청정지수 표시 전환"
          className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 ${showRisks ? "border-[#72EDDA]" : "border-slate-200"}`}>
          <img src={showRisks ? "/icons/cleanliness-on.png" : "/icons/cleanliness-off.png"}
            alt="" aria-hidden="true" className="h-7 w-7 object-contain" />
        </button>
        {audience === "b2g" && (
          <button type="button" onClick={onToggleReports}
            aria-label={showReports ? "제보 숨기기" : "제보 표시"} aria-pressed={showReports}
            title="제보 표시 전환"
            className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 ${showReports ? "border-black" : "border-slate-200"}`}>
            <img src="/icons/user-report.png" alt="" aria-hidden="true" className="h-7 w-7 object-contain" />
          </button>
        )}
        <button type="button" onClick={() => setShowSmokingZones(value => !value)}
          aria-label={showSmokingZones ? "흡연구역 숨기기" : "흡연구역 표시"}
          aria-pressed={showSmokingZones}
          className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 ${showSmokingZones ? "border-black" : "border-slate-200"}`}
          title={showSmokingZones ? "흡연구역 숨기기" : "흡연구역 표시"}>
          <img src="/icons/smoking-zone.png" alt="" aria-hidden="true" className="h-7 w-7 object-contain" />
        </button>
        {audience === "b2c" && onLocate && (
          <button type="button" onClick={onLocate} aria-label="현재 위치로 지도 이동"
            title={currentLocation ? "현재 위치로 지도 이동 (위치 확인됨)" : "현재 위치로 지도 이동 (위치 권한 동의 필요)"}
            className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 border-slate-200`}>
            <img src="/icons/current-location.png" alt="" aria-hidden="true" className="h-7 w-7 object-contain" />
          </button>
        )}
        {audience === "b2c" && onToggleRiskNotice && (
          <div className="relative flex h-11 w-11 shrink-0 items-center justify-center">
            <button type="button" onClick={onToggleRiskNotice}
              aria-label="위험지수 이용 안내"
              aria-expanded={riskNoticeOpen}
              title="위험지수 이용 안내"
              className="flex h-11 w-11 items-center justify-center bg-transparent p-0 text-3xl font-semibold text-slate-800 drop-shadow-sm hover:text-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900">
              <span aria-hidden="true">ⓘ</span>
            </button>
            {riskNoticeOpen && (
              <section role="status" aria-label="위험지수 이용 안내"
                className={`absolute right-[calc(100%+8px)] top-0 z-[800] w-[min(340px,calc(100vw-6rem))] rounded-xl border border-amber-300 bg-amber-50/95 p-3 text-xs leading-5 text-amber-950 shadow-xl transition-opacity duration-[2500ms] ease-in-out ${riskNoticeFading ? "opacity-0 pointer-events-none" : "opacity-100"}`}>
                <div className="flex items-start justify-between gap-2">
                  <strong className="text-sm">위험지수 이용 안내</strong>
                  <button type="button" onClick={onCloseRiskNotice ?? onToggleRiskNotice}
                    aria-label="위험지수 안내 닫기" className="rounded px-1 text-base font-bold">×</button>
                </div>
                <p className="mt-2">
                  이 지도는 보행 환경의 간접흡연 노출 가능성을 예측한 것으로,
                  특정 상점이나 건물의 흡연 발생 여부 또는 책임을 평가하지 않습니다.
                </p>
                <p className="mt-1">
                  위험지수는 위치와 주변 환경에 따른 상대적 참고 정보이며,
                  실제 현장 상황과 다를 수 있습니다.
                </p>
              </section>
            )}
          </div>
        )}
        {showSmokingZones && smokingZonesMessage && (
          <p role="status" className="max-w-52 rounded-lg bg-white/95 p-2 text-xs text-slate-700 shadow">
            {smokingZonesMessage}
          </p>
        )}
        </div>
      </div>

      {audience === "b2g" && showReports && (
        <div className="pointer-events-none absolute bottom-3 left-3 z-[500] flex flex-wrap gap-3 rounded-lg bg-white/95 px-3 py-2 text-xs shadow">
          <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-amber-400" />검토 대기</span>
          <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-green-500" />승인</span>
          <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full bg-slate-400" />반려</span>
        </div>
      )}

      {!import.meta.env.VITE_CARTO_API_KEY && (
        <div role="status" className="pointer-events-none absolute left-3 top-3 z-[500] max-w-64 rounded-lg bg-amber-50/95 px-3 py-2 text-xs text-amber-900 shadow">
          CARTO 지도 API 키가 없습니다. app/frontend/.env.local에 VITE_CARTO_API_KEY를 설정하세요.
        </div>
      )}

    </div>
  );
}
