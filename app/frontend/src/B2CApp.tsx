
import { useCallback, useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import ReportForm from "./components/ReportForm";
import RouteResultPanel from "./components/RouteResultPanel";
import RoutePanel from "./components/RoutePanel";
import MobileB2CSheet from "./components/MobileB2CSheet";
import { lookupAddress } from "./services/addressService";
import { geocodeAddress, type AddressSuggestion } from "./services/addressSearchService";

import type {
  Coordinate,
  Route,
  RouteRequest,
} from "./types/route";

import type {
  Report,
  ReportRequest,
} from "./types/report";

import { getRoutes } from "./services/routeService";
import CleanlinessLegend from "./components/CleanlinessLegend";
import {
  getReports,
  createReport,
} from "./services/reportService";


type PageMode = "shortest" | "safest" | "report";
type LocationMode = "start" | "end";
type SearchStatus = "idle" | "success" | "error";


// =========================================
// 1. 좌표 보조 함수
// =========================================

function formatCoordinate(
  point: Coordinate | null
): string {
  if (!point) return "";

  return (
    `${point[0].toFixed(6)}, ` +
    `${point[1].toFixed(6)}`
  );
}


function parseCoordinate(
  text: string
): Coordinate | null {
  const values = text.split(",");

  if (values.length !== 2) {
    return null;
  }

  if (!values[0].trim() || !values[1].trim()) {
    return null;
  }

  const lat = Number(values[0].trim());
  const lng = Number(values[1].trim());

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


// =========================================
// 2. 메인 컴포넌트
// =========================================

export default function App() {
  // ---------------------------------------
  // 페이지 및 지도 상태
  // ---------------------------------------

  const [pageMode, setPageMode] =
    useState<PageMode>("safest");

  // Tab choice controls which searched route receives per-link cleanliness colors.
  // Keeping it separate from the report tab avoids resetting the route highlight.
  const [selectedRouteId, setSelectedRouteId] = useState<"shortest" | "safest">("safest");

  const [showControls, setShowControls] = useState(false);

  const [selectionMode, setSelectionMode] =
    useState<LocationMode>("start");

  const [focusPoint, setFocusPoint] =
    useState<Coordinate | null>(null);

  // Location consent is requested only when entering B2C. Tracking never moves
  // the map automatically; only a deliberate locate-button click does.
  const [currentLocation, setCurrentLocation] = useState<Coordinate | null>(null);
  const [locationTrackingEnabled, setLocationTrackingEnabled] = useState(false);
  const locationConsentRef = useRef<boolean | null>(null);
  const focusOnNextLocationRef = useRef(false);

  useEffect(() => {
    if (locationConsentRef.current !== null) return;
    if (!navigator.geolocation) {
      locationConsentRef.current = false;
      return;
    }
    const agreed = window.confirm(
      "숨길에서 내 위치를 지도에 표시하기 위해 위치 정보 사용에 동의하시겠습니까? 동의하면 B2C 이용 중 위치가 갱신되며, 지도는 현재 위치 버튼을 누를 때만 이동합니다."
    );
    locationConsentRef.current = agreed;
    setLocationTrackingEnabled(agreed);
  }, []);

  useEffect(() => {
    if (!locationTrackingEnabled || !navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      position => {
        const point: Coordinate = [position.coords.latitude, position.coords.longitude];
        setCurrentLocation(point);
        if (focusOnNextLocationRef.current) {
          focusOnNextLocationRef.current = false;
          setFocusPoint([...point]);
        }
      },
      error => {
        console.warn("현재 위치 추적 오류:", error);
        if (error.code === 1) {
          setLocationTrackingEnabled(false);
          setCurrentLocation(null);
          focusOnNextLocationRef.current = false;
        }
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [locationTrackingEnabled]);

  function focusCurrentLocation() {
    if (!navigator.geolocation) {
      window.alert("이 기기는 위치 기능을 지원하지 않습니다.");
      return;
    }

    // On-demand location lookup avoids relying solely on watchPosition:
    // a watch callback may be delayed by a mobile browser or its permissions.
    navigator.geolocation.getCurrentPosition(
      position => {
        const point: Coordinate = [position.coords.latitude, position.coords.longitude];
        setCurrentLocation(point);
        setFocusPoint([...point]);
        focusOnNextLocationRef.current = false;
      },
      error => {
        const message = error.code === 1
          ? "위치 권한이 거부되었습니다. 브라우저의 사이트 설정에서 위치 권한을 허용해 주세요."
          : error.code === 2
            ? "현재 위치를 확인할 수 없습니다. 기기의 위치 서비스를 켜고 다시 시도해 주세요."
            : "위치 확인 시간이 초과되었습니다. 다시 시도해 주세요.";
        window.alert(message);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );
  }

  // ---------------------------------------
  // 경로 입력 상태
  // ---------------------------------------

  const [start, setStart] =
    useState<Coordinate | null>(null);

  const [end, setEnd] =
    useState<Coordinate | null>(null);

  const [startText, setStartText] = useState("");
  const [endText, setEndText] = useState("");
  // Bind lookup results to their coordinates so an old address never flashes for a new point.
  const [startLookup, setStartLookup] = useState<{ key: string; address: string | null } | null>(null);
  const [endLookup, setEndLookup] = useState<{ key: string; address: string | null } | null>(null);
  const startAddress = start ? (startLookup?.key === start.join(",") ? startLookup.address : undefined) : null;
  const endAddress = end ? (endLookup?.key === end.join(",") ? endLookup.address : undefined) : null;

  // Geocoding is for display only; route coordinates remain unchanged.
  useEffect(() => {
    if (!start) return;
    const controller = new AbortController();
    const key = start.join(",");
    void lookupAddress(start, controller.signal)
      .then(address => { if (!controller.signal.aborted) { setStartLookup({ key, address }); if (address) setStartText(value => value === formatCoordinate(start) ? address : value); } })
      .catch(error => { if (!controller.signal.aborted) { console.warn("출발지 주소 조회:", error); setStartLookup({ key, address: null }); } });
    return () => controller.abort();
  }, [start]);

  useEffect(() => {
    if (!end) return;
    const controller = new AbortController();
    const key = end.join(",");
    void lookupAddress(end, controller.signal)
      .then(address => { if (!controller.signal.aborted) { setEndLookup({ key, address }); if (address) setEndText(value => value === formatCoordinate(end) ? address : value); } })
      .catch(error => { if (!controller.signal.aborted) { console.warn("목적지 주소 조회:", error); setEndLookup({ key, address: null }); } });
    return () => controller.abort();
  }, [end]);

  const [avoidanceLevel, setAvoidanceLevel] =
    useState<RouteRequest["avoidanceLevel"]>(60);

  // ---------------------------------------
  // 경로 탐색 상태
  // ---------------------------------------

  const [routes, setRoutes] =
    useState<Route[]>([]);

  // Show the interpretation notice briefly after an explicit route search.
  // The information button remains available above Leaflet's zoom controls.
  const [showRiskNotice, setShowRiskNotice] = useState(false);
  const [riskNoticeFading, setRiskNoticeFading] = useState(false);
  const riskNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const riskNoticeFadeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function cancelRiskNoticeTimer() {
    if (riskNoticeTimer.current !== null) {
      window.clearTimeout(riskNoticeTimer.current);
      riskNoticeTimer.current = null;
    }
    if (riskNoticeFadeTimer.current !== null) {
      window.clearTimeout(riskNoticeFadeTimer.current);
      riskNoticeFadeTimer.current = null;
    }
  }

  function closeRiskNotice() {
    cancelRiskNoticeTimer();
    setRiskNoticeFading(false);
    setShowRiskNotice(false);
  }

  function showTimedRiskNotice() {
    cancelRiskNoticeTimer();
    setRiskNoticeFading(false);
    setShowRiskNotice(true);
    // Keep the existing total display time (7 seconds), but fade the last 2.5 seconds.
    riskNoticeFadeTimer.current = window.setTimeout(() => {
      setRiskNoticeFading(true);
      riskNoticeFadeTimer.current = null;
    }, 4500);
    riskNoticeTimer.current = window.setTimeout(() => {
      setShowRiskNotice(false);
      setRiskNoticeFading(false);
      riskNoticeTimer.current = null;
    }, 7000);
  }

  function toggleRiskNotice() {
    cancelRiskNoticeTimer();
    setRiskNoticeFading(false);
    setShowRiskNotice(value => !value);
  }

  // Only explicit route searches should zoom/pan to route bounds.
  // Slider-driven recalculation updates the lines without changing the viewport.
  const [fitBoundsRoutes, setFitBoundsRoutes] = useState<Route[]>([]);

  const [loading, setLoading] = useState(false);

  const [searchStatus, setSearchStatus] =
    useState<SearchStatus>("idle");

  const [elapsedSeconds, setElapsedSeconds] =
    useState(0);

  const searchStartTime =
    useRef<number | null>(null);

  const searchInProgress = useRef(false);
  const routeRequestController = useRef<AbortController | null>(null);
  const routeRequestSequence = useRef(0);
  const avoidanceSearchTimer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      cancelRiskNoticeTimer();
      if (avoidanceSearchTimer.current !== null) window.clearTimeout(avoidanceSearchTimer.current);
      routeRequestSequence.current += 1;
      routeRequestController.current?.abort();
    };
  }, []);

  // Path cleanliness comes from scored route segments, not a full-map overlay.
  const [showRisks, setShowRisks] = useState(true);

  // ---------------------------------------
  // 공개 제보 데이터
  // ---------------------------------------

  const [reports, setReports] =
    useState<Report[]>([]);

  const [reportLocation, setReportLocation] =
    useState<Coordinate | null>(null);

  const [reportSubmitting, setReportSubmitting] =
    useState(false);

  const [reportError, setReportError] =
    useState<string | null>(null);

  const [reportNotice, setReportNotice] =
    useState<string | null>(null);

  const [showReports, setShowReports] =
    useState(true);


  // =======================================
  // 3. 공개 제보 목록 재조회
  // =======================================

  const refreshPublicReports = useCallback(
    async (): Promise<void> => {
      try {
        const data = await getReports();

        setReports(data);
        setReportError(null);
      } catch (error) {
        console.error("공개 제보 조회 실패:", error);

        setReportError(
          "공개 제보 목록을 불러오지 못했습니다."
        );
      }
    },
    []
  );


  // =======================================
  // 4. 최초 위험도 및 공개 제보 로드
  // =======================================

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        const reportData = await getReports();

        if (!cancelled) {
          setReports(reportData);
          setReportError(null);
        }
      } catch (error) {
        console.error("제보 조회 실패:", error);

        if (!cancelled) {
          setReportError(
            "공개 제보 목록을 불러오지 못했습니다."
          );
        }
      }
    }

    void loadInitialData();

    return () => {
      cancelled = true;
    };
  }, []);


  // =======================================
  // 5. 실시간 경로 탐색 시간 측정
  // =======================================

  useEffect(() => {
    if (!loading) return;

    const timer = window.setInterval(() => {
      if (searchStartTime.current !== null) {
        setElapsedSeconds(
          (performance.now() -
            searchStartTime.current) / 1000
        );
      }
    }, 100);

    return () => {
      window.clearInterval(timer);
    };
  }, [loading]);


  // =======================================
  // 6. 경로 결과 초기화
  // =======================================

  function cancelPendingRouteSearch() {
    if (avoidanceSearchTimer.current !== null) {
      window.clearTimeout(avoidanceSearchTimer.current);
      avoidanceSearchTimer.current = null;
    }
    routeRequestController.current?.abort();
    routeRequestController.current = null;
    routeRequestSequence.current += 1;
    searchInProgress.current = false;
    searchStartTime.current = null;
    setLoading(false);
  }

  function clearSearchResult() {
    setRoutes([]);

    if (!searchInProgress.current) {
      setElapsedSeconds(0);
      setSearchStatus("idle");
    }
  }


  // =======================================
  // 7. 출발지 또는 목적지 설정
  // =======================================

  function updateLocation(
    mode: LocationMode,
    point: Coordinate,
    textLabel?: string
  ) {
    cancelPendingRouteSearch();
    if (mode === "start") {
      setStart(point);
      setStartLookup(null);
      setStartText(textLabel ?? formatCoordinate(point));
    } else {
      setEnd(point);
      setEndLookup(null);
      setEndText(textLabel ?? formatCoordinate(point));
    }

    setFocusPoint([...point]);
    clearSearchResult();
  }


  // Editing an address invalidates its old coordinates: searches cannot run
  // with stale points while the input shows a different location.
  function handleAddressTextChange(mode: LocationMode, text: string) {
    cancelPendingRouteSearch();
    if (mode === "start") {
      setStartText(text);
      setStart(null);
      setStartLookup(null);
    } else {
      setEndText(text);
      setEnd(null);
      setEndLookup(null);
    }
    clearSearchResult();
  }

  function chooseAddress(mode: LocationMode, suggestion: AddressSuggestion) {
    if (searchInProgress.current) return;
    updateLocation(mode, [suggestion.lat, suggestion.lng], suggestion.address || suggestion.title);
    if (mode === "start") setSelectionMode("end");
  }

  async function applyAddressText(mode: LocationMode): Promise<void> {
    const text = (mode === "start" ? startText : endText).trim();
    if (!text) {
      window.alert("주소 또는 장소명을 입력하세요.");
      return;
    }
    // Preserve the existing coordinate-input behavior.
    const coordinate = parseCoordinate(text);
    if (coordinate) {
      updateLocation(mode, coordinate);
      if (mode === "start") setSelectionMode("end");
      return;
    }
    try {
      const point = await geocodeAddress(text);
      // An async result must not overwrite a newer user edit.
      const current = mode === "start" ? latestStartText.current : latestEndText.current;
      if (current.trim() !== text) return;
      updateLocation(mode, point, text);
      if (mode === "start") setSelectionMode("end");
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "주소를 확인할 수 없습니다.");
    }
  }

  const latestStartText = useRef(startText);
  const latestEndText = useRef(endText);
  latestStartText.current = startText;
  latestEndText.current = endText;

  // =======================================
  // 8. 지도 클릭
  // =======================================

  function handleMapClick(point: Coordinate) {
    if (pageMode === "report") {
      setReportLocation(point);
      setFocusPoint([...point]);
      setReportNotice(null);
      return;
    }

    if (searchInProgress.current) {
      return;
    }

    updateLocation(selectionMode, point);

    if (selectionMode === "start") {
      setSelectionMode("end");
    }
  }


  function swapLocations() {
    if (searchInProgress.current) return;
    cancelPendingRouteSearch();
    setStart(end);
    setEnd(start);
    setStartLookup(endLookup);
    setEndLookup(startLookup);
    setStartText(end ? formatCoordinate(end) : "");
    setEndText(start ? formatCoordinate(start) : "");
    setSelectionMode(start ? "end" : "start");
    setFocusPoint(null);
    clearSearchResult();
  }


  // =======================================
  // 11. A* 경로 탐색
  // =======================================

  async function handleSearch(level: RouteRequest["avoidanceLevel"] = avoidanceLevel, auto = false) {
    if (!start || !end) return;

    // A new slider setting supersedes any pending or in-flight route request.
    if (avoidanceSearchTimer.current !== null) {
      window.clearTimeout(avoidanceSearchTimer.current);
      avoidanceSearchTimer.current = null;
    }
    routeRequestController.current?.abort();
    const controller = new AbortController();
    routeRequestController.current = controller;
    const sequence = ++routeRequestSequence.current;
    searchInProgress.current = true;
    searchStartTime.current = performance.now();

    if (!auto) {
      closeRiskNotice();
    }
    setElapsedSeconds(0);
    setSearchStatus("idle");
    setLoading(true);
    setRoutes([]);

    try {
      const result = await getRoutes({ start, end, avoidanceLevel: level }, controller.signal);
      if (controller.signal.aborted || sequence !== routeRequestSequence.current) return;

      setRoutes(result.routes);
      setSelectedRouteId("safest");
      setSearchStatus("success");
      if (!auto) {
        setFitBoundsRoutes(result.routes);
        // Show route tabs immediately, with avoidance selected initially.
        setShowControls(true);
        setPageMode("safest");
        showTimedRiskNotice();
      }
    } catch (error) {
      if (controller.signal.aborted || sequence !== routeRequestSequence.current) return;
      console.error("경로 탐색 오류:", error);
      setSearchStatus("error");
      if (!auto) {
        window.alert(error instanceof Error ? error.message : "경로 탐색에 실패했습니다.");
      }
    } finally {
      if (sequence === routeRequestSequence.current) {
        if (searchStartTime.current !== null) {
          setElapsedSeconds((performance.now() - searchStartTime.current) / 1000);
        }
        searchStartTime.current = null;
        searchInProgress.current = false;
        routeRequestController.current = null;
        setLoading(false);
      }
    }
  }

  function handleAvoidanceLevelChange(value: RouteRequest["avoidanceLevel"]) {
    if (value === avoidanceLevel) return;
    setAvoidanceLevel(value);
    if (!start || !end) {
      clearSearchResult();
      return;
    }

    // Called only after drag release (or a completed keyboard action).
    // handleSearch aborts the older request and accepts only the latest result.
    void handleSearch(value, true);
  }

  // =======================================
  // 13. 페이지 전환
  // =======================================

  function changePage(mode: PageMode) {
    setPageMode(mode);
    if (mode === "shortest" || mode === "safest") setSelectedRouteId(mode);
    setReportLocation(null);
    setReportNotice(null);


    // 공개 목록은 관리자 검토 후 또는 화면 전환 시 갱신
    if (mode === "shortest" || mode === "report") {
      void refreshPublicReports();
    }
  }


  // =======================================
  // 14. 사용자 제보 등록
  // =======================================

  async function handleCreateReport(
    request: ReportRequest
  ): Promise<boolean> {
    if (reportSubmitting) {
      return false;
    }

    setReportSubmitting(true);
    setReportError(null);
    setReportNotice(null);

    try {
      // PostgreSQL에 pending 상태로 저장
      await createReport(request);

      setReportLocation(null);

      setReportNotice(
        "제보가 등록되어 관리자 검토를 기다리고 있습니다."
      );

      // 등록 직후에도 공개 목록 정책을 유지
      // pending 제보를 지도에 직접 추가하지 않음
      await refreshPublicReports();

      return true;
    } catch (error) {
      console.error("제보 등록 오류:", error);

      setReportError(
        error instanceof Error
          ? error.message
          : "제보 등록에 실패했습니다."
      );

      return false;
    } finally {
      setReportSubmitting(false);
    }
  }


  // =======================================
  // 17. 화면
  // =======================================

  return (
    <div className="flex h-dvh flex-col bg-white soom-b2c-screen">

      {/* 기존 헤더 유지 */}
      <header className="z-[1000] bg-white px-5 py-4 shadow-sm max-[760px]:hidden">
        <h1 className="text-xl font-bold text-green-700">
          숨길
        </h1>

        <p className="text-xs text-gray-500">
          강남구 간접흡연 회피 서비스 · 프로토타입
        </p>
      </header>

      {/* 전체 높이 지도 + 접을 수 있는 설정 패널 */}
      <main className="relative min-h-0 flex-1 soom-b2c-map-area">
        <MapView
          mobileB2C
          start={start}
          end={end}
          routes={routes}
          selectedRouteId={selectedRouteId}
          fitBoundsRoutes={fitBoundsRoutes}
          risks={[]}
          cleanlinessEdges={[]}
          reports={reports}
          showRisks={showRisks}
          showReports={showReports}
          avoidanceLevel={avoidanceLevel}
          onAvoidanceLevelChange={handleAvoidanceLevelChange}
          onToggleCleanliness={() => setShowRisks(value => !value)}
          onToggleReports={() => setShowReports(value => !value)}
          riskNoticeOpen={showRiskNotice}
          riskNoticeFading={riskNoticeFading}
          onToggleRiskNotice={toggleRiskNotice}
          onCloseRiskNotice={closeRiskNotice}
          reportLocation={reportLocation}
          focusPoint={focusPoint}
          selectionMode={selectionMode}
          startAddress={startAddress}
          endAddress={endAddress}
          routeLoading={loading}
          onSearch={() => void handleSearch()}
          onSelectLocation={mode => { if (pageMode === "report") setPageMode("safest"); setSelectionMode(mode); }}
          startInputText={startText}
          endInputText={endText}
          onAddressTextChange={handleAddressTextChange}
          onAddressChoose={chooseAddress}
          onAddressApply={applyAddressText}
          onSwapLocations={swapLocations}
          onLocate={focusCurrentLocation}
          currentLocation={currentLocation}
          onMapClick={handleMapClick}
        />

        <button type="button" onClick={() => setShowControls(value => !value)}
          aria-expanded={showControls}
          className="absolute left-3 top-[140px] max-[760px]:hidden z-[700] rounded-xl border border-slate-200 bg-white/95 px-4 py-2 text-sm font-semibold text-slate-700 shadow-lg">
          {showControls ? "패널 닫기 ×" : "경로 결과 · 제보 ☰"}
        </button>

      {/* 경로 설정과 제보 폼은 필요할 때만 열어서 지도를 가리지 않도록 함 */}
      {showControls && (
      <section className="absolute left-3 top-[188px] max-[760px]:hidden z-[700] max-h-[min(56dvh,calc(100%-206px))] w-[min(390px,calc(100%-24px))] overflow-y-auto rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl">

        {/* 최단/회피 경로 결과와 흡연 제보 탭 */}
        <div className="mb-4 grid grid-cols-3 gap-1">
          {([
            ["shortest", "최단 경로"],
            ["safest", "회피 경로"],
            ["report", "흡연 제보"],
          ] as const).map(([mode, label]) => (
            <button key={mode} type="button" onClick={() => changePage(mode)}
              className={`rounded-lg p-2 text-xs font-bold ${pageMode === mode ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700"}`}>
              {label}
            </button>
          ))}
        </div>

        {pageMode === "shortest" && (
          <RouteResultPanel type="shortest" route={routes.find(route => route.id === "shortest")} />
        )}

        {pageMode === "safest" && (
          <div className="space-y-3">
            <RoutePanel avoidanceLevel={avoidanceLevel} onAvoidanceLevelChange={handleAvoidanceLevelChange} />
            <RouteResultPanel type="safest" route={routes.find(route => route.id !== "shortest")} />
          </div>
        )}

        {loading && <p role="status" className="mt-3 text-xs text-slate-600">경로 계산 중... {elapsedSeconds.toFixed(1)}초</p>}
        {!loading && searchStatus === "error" && <p role="alert" className="mt-3 text-xs text-red-600">경로 탐색에 실패했습니다.</p>}

        {/* 흡연 제보 탭 */}
        {pageMode === "report" && (
          <div className="space-y-3">
            <ReportForm
              location={reportLocation}
              submitting={reportSubmitting}
              onSubmit={handleCreateReport}
              onSelectLocation={() => {
                setReportNotice(null);
              }}
              onCancel={() => changePage("shortest")}
            />

            {reportNotice && (
              <p
                role="status"
                className="rounded-lg bg-green-50 p-3 text-sm text-green-700"
              >
                {reportNotice}
              </p>
            )}
          </div>
        )}

        {reportError && (
          <p
            role="alert"
            className="mt-2 text-xs text-red-600"
          >
            {reportError}
          </p>
        )}

        {(pageMode === "shortest" || pageMode === "safest") && routes.length > 0 && (
          <div className="mt-4 border-t border-slate-200 pt-3">
            <CleanlinessLegend scope="route" embedded />
          </div>
        )}

      </section>
      )}
      <div className="hidden max-[760px]:block">
        <MobileB2CSheet
          pageMode={pageMode}
          onTabChange={changePage}
          routes={routes}
          avoidanceLevel={avoidanceLevel}
          onAvoidanceLevelChange={handleAvoidanceLevelChange}
          loading={loading}
          elapsedSeconds={elapsedSeconds}
          searchError={!loading && searchStatus === "error"}
          reportError={reportError}
          reportContent={
            <div className="space-y-3">
              <ReportForm
                location={reportLocation}
                submitting={reportSubmitting}
                onSubmit={handleCreateReport}
                onSelectLocation={() => setReportNotice(null)}
                onCancel={() => changePage("shortest")}
              />
              {reportNotice && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-700">{reportNotice}</p>}
            </div>
          }
        />
      </div>
      </main>
    </div>
  );
}
