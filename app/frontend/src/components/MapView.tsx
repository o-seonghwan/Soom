
import { useEffect, useState } from "react";
import L from "leaflet";

import {
  MapContainer,
  TileLayer,
  ZoomControl,
  CircleMarker,
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
import "leaflet/dist/leaflet.css";

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
  risks: RiskLocation[];
  cleanlinessEdges?: CleanEdgeFeature[];
  reports: Report[];
  showRisks: boolean;
  showReports: boolean;
  reportLocation: Coordinate | null;
  focusPoint: Coordinate | null;
  selectionMode?: "start" | "end";
  onSelectLocation?: (mode: "start" | "end") => void;
  onSwapLocations?: () => void;
  onLocate?: () => void;
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
  risks,
  cleanlinessEdges,
  reports,
  showRisks,
  showReports,
  reportLocation,
  focusPoint,
  selectionMode = "start",
  onSelectLocation,
  onSwapLocations,
  onLocate,
  onMapClick,
}: MapViewProps) {
  // 실제 강남구 경계 GeoJSON
  const [boundary, setBoundary] =
    useState<GeoJsonObject | null>(null);

  const [boundaryError, setBoundaryError] =
    useState(false);

  const [showSmokingZones, setShowSmokingZones] = useState(false);
  const [smokingZones, setSmokingZones] = useState<Array<{id:string;name:string;lat:number;lng:number}>>([]);
  const [smokingZonesMessage, setSmokingZonesMessage] = useState("");

  useEffect(() => {
    if (!showSmokingZones) return;
    let active = true;
    const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    fetch(`${apiBase}/api/smoking-zones`)
      .then(async response => {
        if (!response.ok) throw new Error(`흡연구역 API 요청 실패 (${response.status})`);
        return await response.json() as {source: string; zones: Array<{id:string;name:string;lat:number;lng:number}>};
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
          setBoundaryError(false);
        }
      } catch (error) {
        console.error(error);

        if (!cancelled) {
          setBoundaryError(true);
        }
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
        <FitRoutes routes={routes} />

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
              fillOpacity: 0.6,
              fillRule: "evenodd",
            }}
          />
        )}

        {/* B2G: 기존 반투명 다색 보행로 유지 */}
        {audience === "b2g" && showRisks && cleanlinessEdges && cleanlinessEdges.length > 0 && (
          <GeoJSON
            key={`clean-roads-b2g-${cleanlinessEdges.length}`}
            data={{ type: "FeatureCollection", features: cleanlinessEdges } as FeatureCollection}
            style={(feature) => ({
              color: getCleanColor(Number(feature?.properties?.cleanIndex ?? 100)),
              weight: 5,
              opacity: 0.36,
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

        {/* 출발지 */}
        {start && (
          <CircleMarker
            center={start}
            radius={9}
            bubblingMouseEvents={false}
            pathOptions={{
              color: "#15803d",
              fillColor: "#22c55e",
              fillOpacity: 1,
            }}
          >
            <Popup>출발지</Popup>
          </CircleMarker>
        )}

        {/* 목적지 */}
        {end && (
          <CircleMarker
            center={end}
            radius={9}
            bubblingMouseEvents={false}
            pathOptions={{
              color: "#b91c1c",
              fillColor: "#ef4444",
              fillOpacity: 1,
            }}
          >
            <Popup>목적지</Popup>
          </CircleMarker>
        )}

        {/* A* 경로 */}
        {routes.map((route) => (
          <Polyline
            key={route.id}
            positions={route.coordinates}
            bubblingMouseEvents={false}
            pathOptions={{
              color:
                route.id === "shortest"
                  ? "#D8DAD3"
                  : "#A68A64",
              weight: route.id === "shortest" ? 5 : 6,
              opacity: 0.95,
            }}
          >
            <Popup>
              <strong>{route.name}</strong>
              <div>거리: {route.distanceM}m</div>
            </Popup>
          </Polyline>
        ))}

        {/* Publicly documented smoking facilities only (no no-smoking data). */}
        {showSmokingZones && smokingZones.map(zone => (
          <CircleMarker key={zone.id} center={[zone.lat, zone.lng]} radius={7}
            bubblingMouseEvents={false}
            pathOptions={{ color: "#92400e", fillColor: "#f59e0b", fillOpacity: 0.9, weight: 2 }}>
            <Popup><strong>{zone.name}</strong><div>흡연구역 위치 자료에 등록된 시설</div></Popup>
          </CircleMarker>
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

      {audience === "b2c" && onSelectLocation && onSwapLocations && (
        <div className="pointer-events-none absolute left-3 top-3 z-[650] w-[min(350px,calc(100%-5.5rem))]">
          <MapRouteCard start={start} end={end} selectionMode={selectionMode}
            onSelect={onSelectLocation} onSwap={onSwapLocations} />
        </div>
      )}

      <div className="absolute right-3 top-3 z-[650] flex flex-col items-end gap-2">
        <button type="button" onClick={() => setShowSmokingZones(value => !value)}
          aria-label={showSmokingZones ? "흡연구역 숨기기" : "흡연구역 표시"}
          aria-pressed={showSmokingZones}
          className={`flex h-11 w-11 items-center justify-center rounded-full border bg-white text-lg shadow-lg ${showSmokingZones ? "border-amber-500 text-amber-700" : "border-slate-200 text-slate-700"}`}
          title={showSmokingZones ? "흡연구역 숨기기" : "흡연구역 표시"}>🚬</button>
        {showSmokingZones && smokingZonesMessage && (
          <p role="status" className="max-w-52 rounded-lg bg-white/95 p-2 text-xs text-slate-700 shadow">
            {smokingZonesMessage}
          </p>
        )}
      </div>

      {audience === "b2c" && onLocate && (
        <button type="button" onClick={onLocate} aria-label="현재 위치로 지도 이동"
          title="현재 위치로 지도 이동 (위치 권한 동의 필요)"
          className="absolute bottom-20 right-3 z-[650] flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-xl text-sky-600 shadow-lg">
          ◎
        </button>
      )}

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
