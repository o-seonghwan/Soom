
import { useCallback, useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import ReportForm from "./components/ReportForm";
import RouteResultPanel from "./components/RouteResultPanel";
import { lookupAddress } from "./services/addressService";

import type {
  Coordinate,
  Route,
  RouteRequest,
} from "./types/route";

import type { RiskLocation } from "./types/risk";
import type {
  Report,
  ReportRequest,
} from "./types/report";

import { getRoutes } from "./services/routeService";
import { getRisks } from "./services/riskService";
import { getB2GCleanEdges } from "./services/cleanlinessService";
import type { CleanEdgeFeature } from "./types/cleanliness";
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
    useState<PageMode>("shortest");

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
      "숨구리당당에서 내 위치를 지도에 표시하기 위해 위치 정보 사용에 동의하시겠습니까? 동의하면 B2C 이용 중 위치가 갱신되며, 지도는 현재 위치 버튼을 누를 때만 이동합니다."
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
      window.alert("현재 위치 기능을 지원하지 않습니다.");
      return;
    }
    if (currentLocation) {
      setFocusPoint([...currentLocation]);
      return;
    }
    // A declined entry consent can be enabled by explicitly tapping locate.
    if (!locationTrackingEnabled) {
      const agreed = window.confirm(
        "내 위치 표시를 활성화하시겠습니까? 동의하면 B2C 이용 중 위치가 계속 갱신됩니다."
      );
      if (!agreed) return;
      locationConsentRef.current = true;
      setLocationTrackingEnabled(true);
    }
    focusOnNextLocationRef.current = true;
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
  const [showCoordinates, setShowCoordinates] = useState(false);

  // Geocoding is for display only; route coordinates remain unchanged.
  useEffect(() => {
    if (!start) return;
    const controller = new AbortController();
    const key = start.join(",");
    void lookupAddress(start, controller.signal)
      .then(address => { if (!controller.signal.aborted) setStartLookup({ key, address }); })
      .catch(error => { if (!controller.signal.aborted) { console.warn("출발지 주소 조회:", error); setStartLookup({ key, address: null }); } });
    return () => controller.abort();
  }, [start]);

  useEffect(() => {
    if (!end) return;
    const controller = new AbortController();
    const key = end.join(",");
    void lookupAddress(end, controller.signal)
      .then(address => { if (!controller.signal.aborted) setEndLookup({ key, address }); })
      .catch(error => { if (!controller.signal.aborted) { console.warn("목적지 주소 조회:", error); setEndLookup({ key, address: null }); } });
    return () => controller.abort();
  }, [end]);

  const [avoidanceLevel, setAvoidanceLevel] =
    useState<RouteRequest["avoidanceLevel"]>(50);

  // ---------------------------------------
  // 경로 탐색 상태
  // ---------------------------------------

  const [routes, setRoutes] =
    useState<Route[]>([]);

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
      if (avoidanceSearchTimer.current !== null) window.clearTimeout(avoidanceSearchTimer.current);
      routeRequestSequence.current += 1;
      routeRequestController.current?.abort();
    };
  }, []);

  // ---------------------------------------
  // 위험도 데이터
  // ---------------------------------------

  const [risks, setRisks] =
    useState<RiskLocation[]>([]);

  const [cleanlinessEdges, setCleanlinessEdges] =
    useState<CleanEdgeFeature[]>([]);

  const [riskLoading, setRiskLoading] =
    useState(true);

  const [riskError, setRiskError] =
    useState<string | null>(null);

  const [showRisks, setShowRisks] =
    useState(true);

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
        const [riskData, edgeData] = await Promise.all([
          getRisks(),
          getB2GCleanEdges(),
        ]);

        if (!cancelled) {
          setRisks(riskData);
          setCleanlinessEdges(edgeData.features);
          setRiskError(null);
        }
      } catch (error) {
        console.error("위험도 조회 실패:", error);

        if (!cancelled) {
          setRisks([]);
          setCleanlinessEdges([]);
          setRiskError(
            "AI 모델 청정지수 보행로를 불러오지 못했습니다. LUNG_RISK_CSV 설정을 확인하세요."
          );
        }
      } finally {
        if (!cancelled) {
          setRiskLoading(false);
        }
      }

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
    point: Coordinate
  ) {
    cancelPendingRouteSearch();
    if (mode === "start") {
      setStart(point);
      setStartLookup(null);
      setStartText(formatCoordinate(point));
    } else {
      setEnd(point);
      setEndLookup(null);
      setEndText(formatCoordinate(point));
    }

    setFocusPoint([...point]);
    clearSearchResult();
  }


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


  // =======================================
  // 9. 직접 입력 좌표 적용
  // =======================================

  function applyCoordinate(mode: LocationMode) {
    if (searchInProgress.current) {
      return;
    }

    const text =
      mode === "start"
        ? startText
        : endText;

    const point = parseCoordinate(text);

    if (!point) {
      window.alert(
        "좌표를 '위도, 경도' 형식으로 입력하세요."
      );
      return;
    }

    updateLocation(mode, point);
  }


  // =======================================
  // 10. 현재 위치를 출발지로 설정
  // =======================================

  function requestCurrentLocation(mode: "start" | "focus") {
    if (searchInProgress.current) return;
    if (!navigator.geolocation) {
      window.alert("현재 위치 기능을 지원하지 않습니다.");
      return;
    }
    const purpose = mode === "start"
      ? "현재 위치를 출발지에 입력하려면 위치 정보 사용에 동의해주세요. 동의한 경우에만 브라우저에 위치 권한을 요청합니다."
      : "현재 위치로 지도를 이동하려면 위치 정보 사용에 동의해주세요. 위치를 경로 출발지로 저장하지 않습니다.";
    if (!window.confirm(purpose)) return;

    navigator.geolocation.getCurrentPosition(
      position => {
        const point: Coordinate = [position.coords.latitude, position.coords.longitude];
        if (mode === "start") {
          updateLocation("start", point);
          setSelectionMode("end");
        } else {
          setFocusPoint([...point]);
        }
      },
      error => {
        console.error("위치 조회 오류:", error);
        window.alert("위치를 확인하지 못했습니다. 브라우저의 위치 접근 권한과 HTTPS 또는 localhost 실행 여부를 확인하세요.");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  }

  function useCurrentLocation() {
    requestCurrentLocation("start");
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

    setElapsedSeconds(0);
    setSearchStatus("idle");
    setLoading(true);
    setRoutes([]);

    try {
      const result = await getRoutes({ start, end, avoidanceLevel: level }, controller.signal);
      if (controller.signal.aborted || sequence !== routeRequestSequence.current) return;

      setRoutes(result.routes);
      setSearchStatus("success");
      if (!auto) {
        // Manual searches keep the existing result-first experience.
        setShowControls(false);
        setPageMode("shortest");
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
  // 12. 경로 초기화
  // =======================================

  function resetRoute() {
    if (searchInProgress.current) {
      return;
    }
    cancelPendingRouteSearch();

    setStart(null);
    setEnd(null);
    setStartLookup(null);
    setEndLookup(null);

    setStartText("");
    setEndText("");

    setFocusPoint(null);
    setSelectionMode("start");

    clearSearchResult();
  }


  // =======================================
  // 13. 페이지 전환
  // =======================================

  function changePage(mode: PageMode) {
    setPageMode(mode);
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
    <div className="flex h-dvh flex-col bg-white">

      {/* 기존 헤더 유지 */}
      <header className="z-[1000] bg-white px-5 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-green-700">
          숨구리당당
        </h1>

        <p className="text-xs text-gray-500">
          강남구 간접흡연 회피 서비스 · 프로토타입
        </p>
      </header>

      {/* 전체 높이 지도 + 접을 수 있는 설정 패널 */}
      <main className="relative min-h-0 flex-1">
        <MapView
          start={start}
          end={end}
          routes={routes}
          risks={risks}
          cleanlinessEdges={cleanlinessEdges}
          reports={reports}
          showRisks={showRisks}
          showReports={showReports}
          avoidanceLevel={avoidanceLevel}
          onAvoidanceLevelChange={handleAvoidanceLevelChange}
          onToggleCleanliness={() => setShowRisks(value => !value)}
          onToggleReports={() => setShowReports(value => !value)}
          reportLocation={reportLocation}
          focusPoint={focusPoint}
          selectionMode={selectionMode}
          startAddress={startAddress}
          endAddress={endAddress}
          routeLoading={loading}
          onSearch={() => void handleSearch()}
          onSelectLocation={setSelectionMode}
          onSwapLocations={swapLocations}
          onLocate={focusCurrentLocation}
          currentLocation={currentLocation}
          onMapClick={handleMapClick}
        />

        {showRisks &&
          !riskLoading &&
          !riskError && cleanlinessEdges.length > 0 && (
            <div className="absolute bottom-3 left-3 z-[500] rounded-xl bg-white/95 p-3 text-xs shadow-lg">
              <p className="font-bold text-slate-800">보행로 청정지수 · AI 모델</p>
              <p className="mt-1 text-gray-600">초록색이 진할수록 청정지수가 높음</p>
              <div className="mt-2 h-2 w-full rounded" style={{background: "linear-gradient(90deg, rgba(22,163,74,0.18), rgba(22,163,74,0.85))"}} />
              <div className="mt-1 flex justify-between text-gray-500"><span>청정지수 낮음</span><span>청정지수 높음</span></div>
              <p className="mt-2 text-[10px] text-gray-500">15레벨 이상 확대 시 표시 · 모델 예측 기반 · 실측 대기질 아님</p>
            </div>
          )}
        <button type="button" onClick={() => setShowControls(value => !value)}
          aria-expanded={showControls}
          className="absolute left-3 top-[124px] z-[700] rounded-xl border border-slate-200 bg-white/95 px-4 py-2 text-sm font-semibold text-slate-700 shadow-lg">
          {showControls ? "패널 닫기 ×" : "경로 결과 · 제보 ☰"}
        </button>

      {/* 경로 설정과 제보 폼은 필요할 때만 열어서 지도를 가리지 않도록 함 */}
      {showControls && (
      <section className="absolute left-3 top-[172px] z-[700] max-h-[min(56dvh,calc(100%-190px))] w-[min(390px,calc(100%-24px))] overflow-y-auto rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl">

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
          <RouteResultPanel type="safest" route={routes.find(route => route.id !== "shortest")} />
        )}

        {loading && <p role="status" className="mt-3 text-xs text-slate-600">경로 계산 중... {elapsedSeconds.toFixed(1)}초</p>}
        {!loading && searchStatus === "error" && <p role="alert" className="mt-3 text-xs text-red-600">경로 탐색에 실패했습니다.</p>}

        {/* 기존 수동 좌표 입력은 별도 접이식 도구로 보존 */}
        {pageMode !== "report" && (
          <div className="mt-3 border-t pt-3">
            <button type="button" onClick={() => setShowCoordinates(value => !value)}
              className="text-xs font-semibold text-slate-600">
              {showCoordinates ? "좌표 직접 입력 닫기 ▲" : "좌표 직접 입력 ▼"}
            </button>
            {showCoordinates && (
              <div className="mt-2 space-y-2">
                {(["start", "end"] as const).map(mode => (
                  <div key={mode} className="flex items-center gap-2">
                    <input aria-label={mode === "start" ? "출발지 좌표" : "목적지 좌표"}
                      placeholder={mode === "start" ? "출발지 위도, 경도" : "목적지 위도, 경도"}
                      value={mode === "start" ? startText : endText}
                      onChange={event => mode === "start" ? setStartText(event.target.value) : setEndText(event.target.value)}
                      className="min-w-0 flex-1 rounded-lg border p-2 text-xs" />
                    <button type="button" onClick={() => applyCoordinate(mode)}
                      className="rounded-lg bg-slate-100 px-3 py-2 text-xs">적용</button>
                  </div>
                ))}
                <button type="button" onClick={useCurrentLocation} className="rounded-lg border px-3 py-2 text-xs">
                  동의 후 현재 위치를 출발지로 지정
                </button>
                <button type="button" onClick={resetRoute} className="ml-2 rounded-lg border px-3 py-2 text-xs">경로 초기화</button>
              </div>
            )}
          </div>
        )}

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

        {riskLoading && (
          <p className="mt-2 text-xs text-gray-500">
            위험도 데이터를 불러오는 중...
          </p>
        )}

        {riskError && (
          <p
            role="alert"
            className="mt-2 text-xs text-red-600"
          >
            {riskError}
          </p>
        )}

        {reportError && (
          <p
            role="alert"
            className="mt-2 text-xs text-red-600"
          >
            {reportError}
          </p>
        )}

        <p className="mt-3 text-xs text-gray-500">
          ※ 청정지수는 모델 위험점수 기반 파생 지표이며 실측 대기질이 아닙니다.
          공개 지도에는 승인된 제보만 표시되며,
          사용자 제보는 위험 회피 A*에 자동으로
          반영되지 않습니다.
        </p>
      </section>
      )}
      </main>
    </div>
  );
}
