
import { useCallback, useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import ReportForm from "./components/ReportForm";
import RoutePanel from "./components/RoutePanel";

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


type PageMode = "route" | "report";
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
    useState<PageMode>("route");

  const [showControls, setShowControls] = useState(false);

  const [selectionMode, setSelectionMode] =
    useState<LocationMode>("start");

  const [focusPoint, setFocusPoint] =
    useState<Coordinate | null>(null);

  // ---------------------------------------
  // 경로 입력 상태
  // ---------------------------------------

  const [start, setStart] =
    useState<Coordinate | null>(null);

  const [end, setEnd] =
    useState<Coordinate | null>(null);

  const [startText, setStartText] = useState("");
  const [endText, setEndText] = useState("");

  const [avoidanceLevel, setAvoidanceLevel] =
    useState<RouteRequest["avoidanceLevel"]>("medium");

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
    setStart(end);
    setEnd(start);
    setStartText(end ? formatCoordinate(end) : "");
    setEndText(start ? formatCoordinate(start) : "");
    setSelectionMode(start ? "end" : "start");
    setFocusPoint(null);
    clearSearchResult();
  }


  // =======================================
  // 11. A* 경로 탐색
  // =======================================

  async function handleSearch() {
    if (
      !start ||
      !end ||
      searchInProgress.current
    ) {
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
        avoidanceLevel,
      });

      setRoutes(result.routes);
      setSearchStatus("success");
      setShowControls(false);
    } catch (error) {
      console.error("경로 탐색 오류:", error);

      setSearchStatus("error");

      window.alert(
        error instanceof Error
          ? error.message
          : "경로 탐색에 실패했습니다."
      );
    } finally {
      if (searchStartTime.current !== null) {
        setElapsedSeconds(
          (performance.now() -
            searchStartTime.current) / 1000
        );
      }

      searchStartTime.current = null;
      searchInProgress.current = false;

      setLoading(false);
    }
  }


  // =======================================
  // 12. 경로 초기화
  // =======================================

  function resetRoute() {
    if (searchInProgress.current) {
      return;
    }

    setStart(null);
    setEnd(null);

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

    if (mode === "route") {
      setSelectionMode(start ? "end" : "start");
    }

    // 공개 목록은 관리자 검토 후 또는 화면 전환 시 갱신
    if (mode === "route" || mode === "report") {
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
          폐(Lung) 끼치지 마세요
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
          reportLocation={reportLocation}
          focusPoint={focusPoint}
          selectionMode={selectionMode}
          onSelectLocation={setSelectionMode}
          onSwapLocations={swapLocations}
          onLocate={() => requestCurrentLocation("focus")}
          onMapClick={handleMapClick}
        />

        {showRisks &&
          !riskLoading &&
          !riskError && cleanlinessEdges.length > 0 && (
            <div className="absolute bottom-14 left-3 z-[500] rounded-xl bg-white/95 p-3 text-xs shadow-lg">
              <p className="font-bold text-slate-800">보행로 청정지수 · AI 모델</p>
              <p className="mt-1 text-gray-600">초록색이 진할수록 청정지수가 높음</p>
              <div className="mt-2 h-2 w-44 rounded" style={{background: "linear-gradient(90deg, rgba(22,163,74,0.18), rgba(22,163,74,0.85))"}} />
              <div className="mt-1 flex justify-between text-gray-500"><span>청정지수 낮음</span><span>청정지수 높음</span></div>
              <p className="mt-2 text-[10px] text-gray-500">15레벨 이상 확대 시 표시 · 모델 예측 기반 · 실측 대기질 아님</p>
            </div>
          )}
        <button type="button" onClick={() => setShowControls(value => !value)}
          aria-expanded={showControls}
          className="absolute left-3 top-36 z-[700] rounded-xl border border-slate-200 bg-white/95 px-4 py-2 text-sm font-semibold text-slate-700 shadow-lg">
          {showControls ? "설정 닫기 ×" : "경로 설정 · 제보 ☰"}
        </button>

      {/* 경로 설정과 제보 폼은 필요할 때만 열어서 지도를 가리지 않도록 함 */}
      {showControls && (
      <section className="absolute left-3 top-48 z-[700] max-h-[min(56dvh,calc(100%-210px))] w-[min(390px,calc(100%-24px))] overflow-y-auto rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-xl">

        {/* 탭 전환 */}
        <div className="mb-4 grid grid-cols-2 gap-2">
          <button
            type="button"
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
            type="button"
            onClick={() => changePage("report")}
            className={`rounded-lg p-3 text-sm font-bold ${
              pageMode === "report"
                ? "bg-purple-600 text-white"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            흡연 제보
          </button>

        </div>

        {/* 경로 탐색 탭 */}
        {pageMode === "route" && (
          <RoutePanel
            start={start}
            end={end}
            startText={startText}
            endText={endText}
            selectionMode={selectionMode}
            avoidanceLevel={avoidanceLevel}
            routes={routes}
            loading={loading}
            elapsedSeconds={elapsedSeconds}
            searchStatus={searchStatus}
            onStartTextChange={setStartText}
            onEndTextChange={setEndText}
            onApplyCoordinate={applyCoordinate}
            onSelectLocation={setSelectionMode}
            onUseCurrentLocation={useCurrentLocation}
            onAvoidanceLevelChange={(value) => {
              setAvoidanceLevel(value);
              clearSearchResult();
            }}
            onSearch={() => void handleSearch()}
            onReset={resetRoute}
          />
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
              onCancel={() => changePage("route")}
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

        {/* 기존 지도 표시 설정 */}
        <div className="mt-4 flex flex-wrap gap-4 border-t pt-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showRisks}
              onChange={(event) =>
                setShowRisks(event.target.checked)
              }
              className="h-4 w-4 accent-green-600"
            />
            보행로 청정지수 표시
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showReports}
              onChange={(event) =>
                setShowReports(event.target.checked)
              }
              className="h-4 w-4 accent-purple-600"
            />
            승인된 제보 표시 ({reports.length})
          </label>
        </div>

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
