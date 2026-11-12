
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

import type { GeoJsonObject } from "geojson";
import type { Coordinate, Route } from "../types/route";
import type { RiskLocation } from "../types/risk";
import type { Report } from "../types/report";

import { getRiskColor } from "../utils/riskColor";
import "leaflet/dist/leaflet.css";

// 강남구 지도 중심 (초기 임시 위치)
const GANGNAM_CENTER: Coordinate = [
  37.4979,
  127.0470,
];

interface MapViewProps {
  start: Coordinate | null;
  end: Coordinate | null;
  routes: Route[];
  risks: RiskLocation[];
  reports: Report[];
  showRisks: boolean;
  showReports: boolean;
  reportLocation: Coordinate | null;
  focusPoint: Coordinate | null;
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

const reportLabels: Record<Report["type"], string> = {
  smoking: "흡연 직접 목격",
  cigarette_butt: "담배꽁초 발견",
  other: "기타 흡연 관련 상황",
};

export default function MapView({
  start,
  end,
  routes,
  risks,
  reports,
  showRisks,
  showReports,
  reportLocation,
  focusPoint,
  onMapClick,
}: MapViewProps) {
  // 실제 강남구 경계 GeoJSON
  const [boundary, setBoundary] =
    useState<GeoJsonObject | null>(null);

  const [boundaryError, setBoundaryError] =
    useState(false);

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
        {/* OpenStreetMap 지도 */}
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <ZoomControl position="bottomright" />

        {/* 지도 입력 및 이동 */}
        <MapClickHandler onMapClick={onMapClick} />
        <MapFocus point={focusPoint} />

        {/* 강남구 전체가 보이도록 초기 조정 */}
        <BoundaryFocus boundary={boundary} />

        {/* 강남구 행정경계 */}
        {boundary && (
          <GeoJSON
            data={boundary}
            interactive={false}
            style={{
              color: "#2563eb",
              weight: 4,
              opacity: 0.95,
              fillOpacity: 0,
              dashArray: undefined,
            }}
          />
        )}

        {/* 위치별 간접흡연 위험도 */}
        {showRisks &&
          risks.map((risk) => (
            <Circle
              key={risk.id}
              center={[risk.lat, risk.lng]}
              radius={risk.radiusM}
              bubblingMouseEvents={false}
              pathOptions={{
                color: getRiskColor(risk.score),
                fillColor: getRiskColor(risk.score),
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
                  ? "#2563eb"
                  : "#16a34a",
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

        {/* 사용자 제보 */}
        {showReports &&
          reports.map((report) => (
            <CircleMarker
              key={report.id}
              center={report.location}
              radius={7}
              bubblingMouseEvents={false}
              pathOptions={{
                color: "#7e22ce",
                fillColor: "#a855f7",
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Popup>
                <strong>
                  {reportLabels[report.type]}
                </strong>

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

      {/* 강남구 경계 안내 */}
      <div className="pointer-events-none absolute right-3 top-3 z-[500] rounded-lg bg-white/95 px-3 py-2 text-xs shadow">
        {boundaryError ? (
          <span className="text-red-600">
            강남구 경계를 불러오지 못했습니다.
          </span>
        ) : boundary ? (
          <div className="flex items-center gap-2">
            <span className="h-1 w-6 rounded bg-blue-600" />
            <span className="font-semibold text-gray-700">
              강남구 행정경계
            </span>
          </div>
        ) : (
          <span className="text-gray-500">
            강남구 경계 로딩 중...
          </span>
        )}
      </div>
    </div>
  );
}
