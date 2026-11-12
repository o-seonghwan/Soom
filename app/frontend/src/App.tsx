
import { useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import RiskLegend from "./components/RiskLegend";
import ReportForm from "./components/ReportForm";
import AdminDashboard from "./components/AdminDashboard";

import type {
  Coordinate,
  Route,
  RouteRequest,
} from "./types/route";

import type { RiskLocation } from "./types/risk";
import type { Report, ReportRequest } from "./types/report";

import { getRoutes } from "./services/routeService";
import { getRisks } from "./services/riskService";
import {
  getReports,
  createReport,
} from "./services/reportService";

type SelectionMode = "start" | "end" | "report";
type PageMode = "route" | "report" | "admin";
type SearchStatus = "idle" | "success" | "error";

function formatCoordinate(point: Coordinate | null): string {
  if (!point) return "";
  return `${point[0].toFixed(6)}, ${point[1].toFixed(6)}`;
}

function parseCoordinate(value: string): Coordinate | null {
  const parts = value.split(",");

  if (parts.length !== 2) return null;
  if (!parts[0].trim() || !parts[1].trim()) return null;

  const lat = Number(parts[0].trim());
  const lng = Number(parts[1].trim());

  if (
    !Number.isFinite(lat) ||
    !Number.isFinite(lng) ||
    lat < -90 ||
    lat > 90 ||
    lng < -180 ||
    lng > 180
  ) {
    return null;
  }

  return [lat, lng];
}

export default function App() {
  // =====================================================
  // 1. 화면 및 지도 설정
  // =====================================================

  const [pageMode, setPageMode] =
    useState<PageMode>("route");

  const [selectionMode, setSelectionMode] =
    useState<SelectionMode>("start");

  const [focusPoint, setFocusPoint] =
    useState<Coordinate | null>(null);

  // =====================================================
  // 2. 출발지 및 목적지
  // =====================================================

  const [start, setStart] =
    useState<Coordinate | null>(null);

  const [end, setEnd] =
    useState<Coordinate | null>(null);

  const [startText, setStartText] = useState("");
  const [endText, setEndText] = useState("");

  // =====================================================
  // 3. 경로 탐색 및 소요 시간
  // =====================================================

  const [routes, setRoutes] = useState<Route[]>([]);

  const [level, setLevel] =
    useState<RouteRequest["avoidanceLevel"]>("medium");

  const [loading, setLoading] = useState(false);

  const [elapsedSeconds, setElapsedSeconds] =
    useState(0);

  const [searchStatus, setSearchStatus] =
    useState<SearchStatus>("idle");

  const searchStartTime = useRef<number | null>(null);
  const searchInProgress = useRef(false);

  // =====================================================
  // 4. 위험도 데이터
  // =====================================================

  const [risks, setRisks] =
    useState<RiskLocation[]>([]);

  const [showRisks, setShowRisks] = useState(true);
  const [riskLoading, setRiskLoading] = useState(true);

  const [riskError, setRiskError] =
    useState<string | null>(null);

  // =====================================================
  // 5. 사용자 제보
  // =====================================================

  const [reports, setReports] = useState<Report[]>([]);

  const [reportLocation, setReportLocation] =
    useState<Coordinate | null>(null);

  const [showReports, setShowReports] = useState(true);

  const [reportSubmitting, setReportSubmitting] =
    useState(false);

  const [reportError, setReportError] =
    useState<string | null>(null);

  // =====================================================
  // 6. 위험도 및 제보 데이터 조회
  // =====================================================

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const data = await getRisks();

        if (!cancelled) {
          setRisks(data);
          setRiskError(null);
        }
      } catch (error) {
        console.error(error);

        if (!cancelled) {
          setRisks([]);
          setRiskError("위험도 조회에 실패했습니다.");
        }
      } finally {
        if (!cancelled) {
          setRiskLoading(false);
        }
      }

      try {
        const data = await getReports();

        if (!cancelled) {
          setReports(data);
          setReportError(null);
        }
      } catch (error) {
        console.error(error);

        if (!cancelled) {
          setReportError(
            "제보 목록을 불러오지 못했습니다."
          );
        }
      }
    }

    void loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  // =====================================================
  // 7. 실시간 경로 탐색 시간 측정
  // =====================================================

  useEffect(() => {
    if (!loading) return;

    const timer = window.setInterval(() => {
      if (searchStartTime.current !== null) {
        setElapsedSeconds(
          (performance.now() - searchStartTime.current)
          / 1000
        );
      }
    }, 100);

    return () => {
      window.clearInterval(timer);
    };
  }, [loading]);

  // =====================================================
  // 8. 기존 경로 탐색 결과 초기화
  // =====================================================

  function clearSearchResult() {
    setRoutes([]);

    if (!searchInProgress.current) {
      setElapsedSeconds(0);
      setSearchStatus("idle");
    }
  }

  // =====================================================
  // 9. 출발지 및 목적지 변경
  // =====================================================

  function updateLocation(
    mode: "start" | "end",
    point: Coordinate
  ) {
    if (mode === "start") {
      setStart(point);
      setStartText(formatCoordinate(point));
    } else {
      setEnd(point);
      setEndText(formatCoordinate(point));
    }

    setFocusPoint([...point]);
    clearSearchResult();
  }

  // =====================================================
  // 10. 지도 클릭 처리
  // =====================================================

  function handleMapClick(point: Coordinate) {
    if (pageMode === "admin") return;

    if (pageMode === "report") {
      setReportLocation(point);
      setFocusPoint([...point]);
      return;
    }

    // 탐색 중 좌표 변경 방지
    if (searchInProgress.current) return;
    if (selectionMode === "report") return;

    updateLocation(selectionMode, point);

    if (selectionMode === "start") {
      setSelectionMode("end");
    }
  }

  // =====================================================
  // 11. 좌표 직접 입력
  // =====================================================

  function applyCoordinate(mode: "start" | "end") {
    if (searchInProgress.current) return;

    const text =
      mode === "start" ? startText : endText;

    const point = parseCoordinate(text);

    if (!point) {
      alert("좌표를 '위도, 경도' 형식으로 입력하세요.");
      return;
    }

    updateLocation(mode, point);
  }

  // =====================================================
  // 12. 현재 위치를 출발지로 설정
  // =====================================================

  function useCurrentLocation() {
    if (searchInProgress.current) return;

    if (!navigator.geolocation) {
      alert("현재 위치 기능을 지원하지 않습니다.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (searchInProgress.current) return;

        const point: Coordinate = [
          position.coords.latitude,
          position.coords.longitude,
        ];

        updateLocation("start", point);
        setSelectionMode("end");
      },
      (error) => {
        console.error(error);
        alert("현재 위치 확인에 실패했습니다.");
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }

  // =====================================================
  // 13. 실제 A* 경로 탐색
  // =====================================================

  async function handleSearch() {
    if (!start || !end || searchInProgress.current) {
      return;
    }

    searchInProgress.current = true;
    searchStartTime.current = performance.now();

    setElapsedSeconds(0);
    setSearchStatus("idle");
    setLoading(true);
    setRoutes([]);

    try {
      const result = await getRoutes({
        start,
        end,
        avoidanceLevel: level,
      });

      setRoutes(result.routes);
      setSearchStatus("success");
    } catch (error) {
      console.error(error);
      setSearchStatus("error");

      alert(
        error instanceof Error
          ? error.message
          : "경로를 불러오지 못했습니다."
      );
    } finally {
      if (searchStartTime.current !== null) {
        const totalTime =
          (performance.now() - searchStartTime.current)
          / 1000;

        setElapsedSeconds(totalTime);
      }

      searchStartTime.current = null;
      searchInProgress.current = false;
      setLoading(false);
    }
  }

  // =====================================================
  // 14. 경로 초기화
  // =====================================================

  function resetRoute() {
    if (searchInProgress.current) return;

    setStart(null);
    setEnd(null);

    setStartText("");
    setEndText("");

    clearSearchResult();

    setFocusPoint(null);
    setSelectionMode("start");
  }

  // =====================================================
  // 15. 페이지 전환
  // =====================================================

  function changePage(mode: PageMode) {
    setPageMode(mode);
    setReportLocation(null);

    if (mode === "report") {
      setSelectionMode("report");
    } else {
      setSelectionMode(start ? "end" : "start");
    }
  }

  // =====================================================
  // 16. 사용자 제보 등록
  // =====================================================

  async function handleCreateReport(
    request: ReportRequest
  ): Promise<boolean> {
    if (reportSubmitting) return false;

    setReportSubmitting(true);
    setReportError(null);

    try {
      const saved = await createReport(request);

      setReports((current) => [...current, saved]);
      setReportLocation(null);

      alert("프로토타입 제보가 등록되었습니다.");

      return true;
    } catch (error) {
      console.error(error);
      setReportError("제보 등록에 실패했습니다.");

      return false;
    } finally {
      setReportSubmitting(false);
    }
  }

  // =====================================================
  // 17. 관리자 화면에서 위치 확인
  // =====================================================

  function focusReportLocation(point: Coordinate) {
    setFocusPoint([...point]);
    setShowReports(true);
  }

  // =====================================================
  // 18. 화면 렌더링
  // =====================================================

  return (
    <div className="flex h-dvh flex-col bg-white">

      {/* 상단 헤더 */}
      <header className="z-[1000] bg-white px-5 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-green-700">
          폐(Lung) 끼치지 마세요
        </h1>

        <p className="text-xs text-gray-500">
          강남구 간접흡연 회피 서비스 · 프로토타입
        </p>
      </header>

      {/* 지도 */}
      <main className="relative min-h-0 flex-1">
        <MapView
          start={start}
          end={end}
          routes={routes}
          risks={risks}
          reports={reports}
          showRisks={showRisks}
          showReports={showReports}
          reportLocation={reportLocation}
          focusPoint={focusPoint}
          onMapClick={handleMapClick}
        />

        {showRisks && !riskLoading && !riskError && (
          <RiskLegend />
        )}
      </main>

      {/* 하단 기능 패널 */}
      <section className="z-[1000] max-h-[55dvh] overflow-y-auto bg-white p-4 shadow-lg">

        {/* 페이지 전환 */}
        <div className="mb-4 grid grid-cols-3 gap-2">

          <button
            onClick={() => changePage("route")}
            className={`rounded-lg p-3 text-sm font-bold ${
              pageMode === "route"
                ? "bg-green-600 text-white"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            경로 탐색
          </button>

          <button
            onClick={() => changePage("report")}
            className={`rounded-lg p-3 text-sm font-bold ${
              pageMode === "report"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            흡연 제보
          </button>

          <button
            onClick={() => changePage("admin")}
            className={`rounded-lg p-3 text-sm font-bold ${
              pageMode === "admin"
                ? "bg-slate-700 text-white"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            관리자
          </button>

        </div>

        {/* ========================================= */}
        {/* 경로 탐색 화면 */}
        {/* ========================================= */}

        {pageMode === "route" ? (
          <div className="space-y-3">

            <p className="text-sm text-gray-600">
              지도 선택 모드:{" "}
              <strong className="text-green-700">
                {selectionMode === "start"
                  ? "출발지"
                  : "목적지"}
              </strong>
            </p>

            {/* 출발지 */}
            <div className="space-y-1">
              <label
                htmlFor="start-coordinate"
                className="text-sm font-bold"
              >
                출발지
              </label>

              <div className="flex flex-wrap gap-2">
                <input
                  id="start-coordinate"
                  type="text"
                  value={startText}
                  disabled={loading}
                  onChange={(e) =>
                    setStartText(e.target.value)
                  }
                  placeholder="위도, 경도"
                  className="min-w-0 flex-1 rounded-lg border p-3 text-sm"
                />

                <button
                  disabled={loading}
                  onClick={() => applyCoordinate("start")}
                  className="rounded-lg bg-gray-100 px-3 text-sm disabled:opacity-50"
                >
                  적용
                </button>

                <button
                  disabled={loading}
                  onClick={() => setSelectionMode("start")}
                  className={`rounded-lg px-3 text-sm disabled:opacity-50 ${
                    selectionMode === "start"
                      ? "bg-green-600 text-white"
                      : "bg-green-100 text-green-800"
                  }`}
                >
                  지도 선택
                </button>

                <button
                  disabled={loading}
                  onClick={useCurrentLocation}
                  className="rounded-lg border px-3 text-sm disabled:opacity-50"
                >
                  현재 위치
                </button>
              </div>
            </div>

            {/* 목적지 */}
            <div className="space-y-1">
              <label
                htmlFor="end-coordinate"
                className="text-sm font-bold"
              >
                목적지
              </label>

              <div className="flex flex-wrap gap-2">
                <input
                  id="end-coordinate"
                  type="text"
                  value={endText}
                  disabled={loading}
                  onChange={(e) =>
                    setEndText(e.target.value)
                  }
                  placeholder="위도, 경도"
                  className="min-w-0 flex-1 rounded-lg border p-3 text-sm"
                />

                <button
                  disabled={loading}
                  onClick={() => applyCoordinate("end")}
                  className="rounded-lg bg-gray-100 px-3 text-sm disabled:opacity-50"
                >
                  적용
                </button>

                <button
                  disabled={loading}
                  onClick={() => setSelectionMode("end")}
                  className={`rounded-lg px-3 text-sm disabled:opacity-50 ${
                    selectionMode === "end"
                      ? "bg-green-600 text-white"
                      : "bg-green-100 text-green-800"
                  }`}
                >
                  지도 선택
                </button>
              </div>
            </div>

            {/* 회피 강도 */}
            <div className="space-y-1">
              <label
                htmlFor="avoidance-level"
                className="text-sm font-bold"
              >
                간접흡연 회피 강도
              </label>

              <select
                id="avoidance-level"
                value={level}
                disabled={loading}
                onChange={(e) => {
                  setLevel(
                    e.target.value as
                    RouteRequest["avoidanceLevel"]
                  );

                  clearSearchResult();
                }}
                className="w-full rounded-lg border p-3 text-sm"
              >
                <option value="low">낮음</option>
                <option value="medium">보통</option>
                <option value="high">높음</option>
              </select>

              <p className="text-xs text-gray-500">
                현재 일반 최단경로에는 회피 강도가 적용되지 않습니다.
              </p>
            </div>

            {/* 경로 탐색 및 초기화 */}
            <div className="flex gap-2">
              <button
                disabled={!start || !end || loading}
                onClick={handleSearch}
                className="flex-1 rounded-lg bg-green-600 p-3 font-bold text-white disabled:bg-gray-300"
              >
                {loading ? "탐색 중..." : "경로 탐색"}
              </button>

              <button
                disabled={loading}
                onClick={resetRoute}
                className="rounded-lg border px-5 py-3 disabled:opacity-50"
              >
                초기화
              </button>
            </div>

            {/* 탐색 중 실시간 경과 시간 */}
            {loading && (
              <div
                role="status"
                className="rounded-lg border border-blue-200 bg-blue-50 p-3"
              >
                <p className="text-sm font-bold text-blue-700">
                  A* 경로 탐색 중...
                </p>

                <p className="mt-1 text-xl font-bold text-blue-800">
                  {elapsedSeconds.toFixed(1)}초 경과
                </p>

                <p className="mt-1 text-xs text-blue-600">
                  저장된 강남구 보행 네트워크를 이용해 계산합니다.
                </p>
              </div>
            )}

            {/* 탐색 완료 */}
            {!loading && searchStatus === "success" && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                <p className="text-sm font-bold text-green-700">
                  경로 탐색 완료
                </p>

                <p className="mt-1 text-lg font-bold text-green-800">
                  {elapsedSeconds.toFixed(1)}초 소요
                </p>
              </div>
            )}

            {/* 탐색 실패 */}
            {!loading && searchStatus === "error" && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-bold text-red-700">
                  경로 탐색 실패
                </p>

                <p className="mt-1 text-lg font-bold text-red-800">
                  {elapsedSeconds.toFixed(1)}초 경과
                </p>
              </div>
            )}

            {/* 경로 탐색 결과 */}
            {routes.length > 0 && (
              <div className="space-y-2">

                {routes.map((route) => (
                  <div
                    key={route.id}
                    className="rounded-lg border border-blue-100 bg-blue-50 p-4"
                  >
                    <p className="font-bold text-blue-800">
                      {route.name}
                    </p>

                    <div className="mt-2 grid grid-cols-2 gap-3">

                      <div>
                        <p className="text-xs text-gray-500">
                          경로 거리
                        </p>
                        <p className="text-lg font-bold">
                          {route.distanceM.toLocaleString()}m
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">
                          예상 도보 시간
                        </p>
                        <p className="text-lg font-bold">
                          {route.estimatedMinutes !== undefined
                            ? `약 ${route.estimatedMinutes.toFixed(1)}분`
                            : "정보 없음"}
                        </p>
                      </div>

                    </div>

                    {/* 보행 링크 접속 정보 */}
                    {route.startSnapDistanceM !== undefined &&
                      route.endSnapDistanceM !== undefined && (
                        <div className="mt-3 rounded-lg bg-white p-3 text-xs text-gray-600">
                          <p className="font-bold text-gray-700">
                            보행로 연결 정보
                          </p>

                          <p className="mt-1">
                            출발지 → 보행로:{" "}
                            {route.startSnapDistanceM.toFixed(1)}m
                          </p>

                          <p>
                            목적지 → 보행로:{" "}
                            {route.endSnapDistanceM.toFixed(1)}m
                          </p>

                          <p className="mt-2 text-gray-500">
                            위 거리는 클릭 위치에서 보행 링크까지의
                            직선거리이며, 경로 거리에는 포함되지 않습니다.
                          </p>
                        </div>
                      )}

                  </div>
                ))}
              </div>
            )}

          </div>

        ) : pageMode === "report" ? (

          /* 사용자 제보 */

          <ReportForm
            location={reportLocation}
            submitting={reportSubmitting}
            onSubmit={handleCreateReport}
            onSelectLocation={() =>
              setSelectionMode("report")
            }
            onCancel={() => changePage("route")}
          />

        ) : (

          /* 관리자 대시보드 */

          <AdminDashboard
            reports={reports}
            risks={risks}
            onFocusLocation={focusReportLocation}
          />

        )}

        {/* 공통 지도 표시 설정 */}
        <div className="mt-4 flex flex-wrap gap-4 border-t pt-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showRisks}
              onChange={(e) =>
                setShowRisks(e.target.checked)
              }
              className="h-4 w-4 accent-green-600"
            />
            위험지역 표시
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showReports}
              onChange={(e) =>
                setShowReports(e.target.checked)
              }
              className="h-4 w-4 accent-purple-600"
            />
            사용자 제보 표시 ({reports.length})
          </label>
        </div>

        {/* 위험도 데이터 상태 */}
        {riskLoading && (
          <p className="mt-2 text-xs text-gray-500">
            위험도 데이터를 불러오는 중...
          </p>
        )}

        {riskError && (
          <p role="alert" className="mt-2 text-xs text-red-600">
            {riskError}
          </p>
        )}

        {/* 제보 데이터 상태 */}
        {reportError && (
          <p role="alert" className="mt-2 text-xs text-red-600">
            {reportError}
          </p>
        )}

        <p className="mt-3 text-xs text-gray-500">
          ※ 현재 위험도와 제보는 프로토타입 데이터입니다.
          일반 경로는 OSM 보행 네트워크 기반이며,
          실제 도보 안내용으로 검증되지 않았습니다.
        </p>

      </section>
    </div>
  );
}
