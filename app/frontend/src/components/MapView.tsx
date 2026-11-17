
import { useEffect, useState } from "react";
import L from "leaflet";

import {
  MapContainer,
  TileLayer,
  ZoomControl,
  CircleMarker,
  Marker,
  Circle,
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
import B2CCleanRoads from "./B2CCleanRoads";
import MapRouteCard from "./MapRouteCard";
import RoutePanel from "./RoutePanel";
import type { RouteRequest } from "../types/route";
import { deduplicateCleanEdges } from "../utils/deduplicateCleanEdges";
import "leaflet/dist/leaflet.css";

// Smoking-area positions use the same cigarette pictogram as the layer toggle.
// Inline DivIcon avoids external icon asset paths and stays legible at any map zoom.
const smokingZoneIcon = L.divIcon({
  className: "lung-smoking-zone-icon",
  html: '<span aria-hidden="true" style="display:flex;align-items:center;justify-content:center;width:32px;height:32px;border:2px solid #92400e;border-radius:50%;background:#fff7ed;box-shadow:0 2px 7px rgba(0,0,0,.25);font-size:19px;line-height:1">🚬</span>',
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
  fitBoundsRoutes?: Route[];
  risks: RiskLocation[];
  cleanlinessEdges?: CleanEdgeFeature[];
  reports: Report[];
  showRisks: boolean;
  showReports: boolean;
  avoidanceLevel?: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange?: (value: RouteRequest["avoidanceLevel"]) => void;
  onToggleCleanliness?: () => void;
  onToggleReports?: () => void;
  reportLocation: Coordinate | null;
  focusPoint: Coordinate | null;
  selectionMode?: "start" | "end";
  startAddress?: string | null;
  endAddress?: string | null;
  routeLoading?: boolean;
  onSearch?: () => void;
  onSelectLocation?: (mode: "start" | "end") => void;
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
  fitBoundsRoutes = routes,
  risks,
  cleanlinessEdges,
  reports,
  showRisks,
  showReports,
  avoidanceLevel,
  onAvoidanceLevelChange,
  onToggleCleanliness,
  onToggleReports,
  reportLocation,
  focusPoint,
  selectionMode = "start",
  startAddress,
  endAddress,
  routeLoading = false,
  onSearch,
  onSelectLocation,
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
            style={(feature) => ({
              color: getCleanColor(Number(feature?.properties?.cleanIndex ?? 100)),
              weight: 3,
              opacity: 0.36,
              lineCap: "round",
              lineJoin: "round",
            })}
            onEachFeature={(feature, layer) => {
              const clean = Number(feature.properties?.cleanIndex ?? 100);
              const risk = Number(feature.properties?.score ?? 0);
              layer.bindPopup(`보행 링크 청정지수: ${clean.toFixed(1)}/100<br/>유효 위험점수: ${risk.toFixed(1)}/100`);
            }}
          />
        )}

        {/* B2C: 초록색 단일 Canvas, 픽셀별 최대 불투명도만 적용 */}
        {audience === "b2c" && showRisks && cleanlinessEdges && cleanlinessEdges.length > 0 && (
          <B2CCleanRoads edges={cleanlinessEdges} />
        )}

        {/* 구형 데이터 사용 화면에만 기존 위험 원형 유지. 모델 보행로와 중복 표시하지 않음. */}
        {audience === "b2c" && !cleanlinessEdges && showRisks &&
          risks.map((risk) => (
            <Circle
              key={risk.id}
              center={[risk.lat, risk.lng]}
              radius={risk.radiusM}
              bubblingMouseEvents={false}
              pathOptions={{
                color: "#64748b",
                fillColor: "#93c5d6",
                fillOpacity: 0.35,
                weight: 1,
              }}
            >
              <Popup>
                <strong>간접흡연 위험도</strong>
                <div>
                  위험점수: {risk.score}/100
                </div>
              </Popup>
            </Circle>
          ))}

        {/* A* 경로 */}
        {routes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.coordinates}
            bubblingMouseEvents={false}
            pathOptions={{
              color:
                route.id === "shortest"
                  ? "#343A40"
                  : "#72EFDD",
              weight: route.id === "shortest" ? 5 : 6,
              opacity: 0.98,
              lineCap: "round",
              lineJoin: "round",
            }}
          >
            <Popup>
              <strong>{route.name}</strong>
              <div>거리: {route.distanceM}m</div>
            </Popup>
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

      {audience === "b2c" && onSelectLocation && onSwapLocations && onSearch && (
        <div className="pointer-events-none absolute left-3 top-3 z-[650] w-[min(440px,calc(100%-5.5rem))]">
          <MapRouteCard start={start} end={end} selectionMode={selectionMode}
            startAddress={startAddress} endAddress={endAddress} loading={routeLoading}
            onSelect={onSelectLocation} onSwap={onSwapLocations} onSearch={onSearch} />
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
          className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 ${showRisks ? "border-black" : "border-slate-200"}`}>
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
            className={`flex h-11 w-11 items-center justify-center rounded-full border-2 bg-white shadow-lg transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900 ${currentLocation ? "border-black" : "border-slate-200"}`}>
            <img src="/icons/current-location.png" alt="" aria-hidden="true" className="h-7 w-7 object-contain" />
          </button>
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
