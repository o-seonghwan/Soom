
import { useCallback, useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import AdminDashboard from "./components/AdminDashboard";
import { getB2GCleanEdges } from "./services/cleanlinessService";
import type { CleanEdgeFeature } from "./types/cleanliness";
import CleanlinessLegend from "./components/CleanlinessLegend";
import DbscanSitePanel from "./components/DbscanSitePanel";
import { getDbscanSites } from "./services/dbscanService";
import type { DbscanSitesResponse, DbscanCandidate } from "./types/dbscan";
import ChildcareExposurePanel from "./components/ChildcareExposurePanel";
import { getChildcareExposure } from "./services/childcareService";
import type { ChildcareExposureResponse, ChildcareExposure } from "./types/childcare";

import { getReports } from "./services/reportService";
import { getRisks } from "./services/riskService";

import type { Coordinate } from "./types/route";
import type { Report } from "./types/report";
import type { RiskLocation } from "./types/risk";

export default function B2GDashboard() {
  // 공개 신고 및 관리자 신고
  const [publicReports, setPublicReports] =
    useState<Report[]>([]);

  const [adminReports, setAdminReports] =
    useState<Report[] | null>(null);

  // 위험지역
  const [risks, setRisks] =
    useState<RiskLocation[]>([]);

  const [cleanEdges, setCleanEdges] = useState<CleanEdgeFeature[]>([]);
  const [dataSource, setDataSource] = useState<"model-csv" | null>(null);

  // 지도 표시 옵션
  const [showReports, setShowReports] =
    useState(true);

  const [showRisks, setShowRisks] =
    useState(true);
  const [showDashboard, setShowDashboard] = useState(false);
  const [analysisTab, setAnalysisTab] = useState<"reports" | "dbscan" | "childcare">("reports");
  const [dashboardTarget, setDashboardTarget] = useState<HTMLDivElement | null>(null);
  const authHeaderRef = useRef<string | null>(null);
  const [dbscanSites, setDbscanSites] = useState<DbscanSitesResponse | null>(null);
  const [childcareData, setChildcareData] = useState<ChildcareExposureResponse | null>(null);
  const [childcareLoading, setChildcareLoading] = useState(false);
  const [childcareError, setChildcareError] = useState("");
  const [selectedChildcare, setSelectedChildcare] = useState<ChildcareExposure | null>(null);
  const [dbscanLoading, setDbscanLoading] = useState(false);
  const [dbscanError, setDbscanError] = useState("");
  const [selectedDbscanCluster, setSelectedDbscanCluster] = useState<string | null>(null);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [adminAuthorized, setAdminAuthorized] = useState(false);
  const [logoutSignal, setLogoutSignal] = useState(0);

  const [focusPoint, setFocusPoint] =
    useState<Coordinate | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  // The authenticated session is supplied by the already-mounted login controller.
  // Results are never shown or loaded before successful administrator login.
  function handleSessionChange(header: string | null) {
    authHeaderRef.current = header;
    if (!header) {
      setDbscanSites(null);
      setChildcareData(null);
      setChildcareLoading(false);
      setChildcareError("");
      setSelectedChildcare(null);
      setDbscanError("");
      setDbscanLoading(false);
      setSelectedDbscanCluster(null);
      setAnalysisTab("reports");
      setShowDashboard(false);
    }
  }

  async function loadDbscanSites() {
    const header = authHeaderRef.current;
    if (!header) return;
    setDbscanLoading(true);
    setDbscanError("");
    try {
      const result = await getDbscanSites(header);
      // A late network response must not restore private data after logout.
      if (authHeaderRef.current === header) {
        setDbscanSites(result);
        // Default to the first actual hotspot, not "전체 적발 집중지".
        // Preserve a manually selected filter (including "all") on reload.
        setSelectedDbscanCluster(current => {
          if (current === null || (current !== "" && !result.clusters.some(c => c.id === current))) {
            return result.clusters[0]?.id ?? "";
          }
          return current;
        });
      }
    } catch (err) {
      if (authHeaderRef.current !== header) return;
      setDbscanSites(null);
      setDbscanError(err instanceof Error ? err.message : "입지 후보 데이터 조회 실패");
    } finally {
      if (authHeaderRef.current === header) setDbscanLoading(false);
    }
  }

  async function loadChildcareExposure() {
    const header = authHeaderRef.current;
    if (!header) return;
    setChildcareLoading(true);
    setChildcareError("");
    try {
      const result = await getChildcareExposure(header);
      if (authHeaderRef.current === header) setChildcareData(result);
    } catch (err) {
      if (authHeaderRef.current !== header) return;
      setChildcareData(null);
      setChildcareError(err instanceof Error ? err.message : "어린이집 노출순위 조회 실패");
    } finally {
      if (authHeaderRef.current === header) setChildcareLoading(false);
    }
  }

  function selectAnalysisTab(tab: "reports" | "dbscan" | "childcare") {
    setAnalysisTab(tab);
    if (tab !== "childcare") setSelectedChildcare(null);
    if (tab === "dbscan" && !dbscanSites && !dbscanLoading) void loadDbscanSites();
    if (tab === "childcare" && !childcareData && !childcareLoading) void loadChildcareExposure();
  }

  function focusChildcare(nursery: ChildcareExposure) {
    setSelectedChildcare(nursery);
    setFocusPoint([nursery.lat, nursery.lng]);
    setShowDashboard(false);
  }

  function focusDbscanCandidate(candidate: DbscanCandidate) {
    setFocusPoint([candidate.lat, candidate.lng]);
    setShowDashboard(false);
  }

  // 공개 신고 최신 목록 조회
  const refreshPublicReports = useCallback(
    async (): Promise<void> => {
      try {
        const data = await getReports();

        setPublicReports(data);
      } catch (err) {
        console.error("공개 신고 조회 실패:", err);
        setError(
          "공개 신고 데이터를 불러오지 못했습니다."
        );
      }
    },
    []
  );

  // 초기 지도 데이터 조회
  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setLoading(true);

      try {
        const results = await Promise.allSettled([
          getReports(),
          getRisks(),
          getB2GCleanEdges(),
        ]);

        if (cancelled) return;

        if (results[0].status === "fulfilled") {
          setPublicReports(results[0].value);
        } else {
          console.error(results[0].reason);
          setError(
            "공개 신고 데이터를 불러오지 못했습니다."
          );
        }

        // B2G 모델 지수/위험 지점은 모두 실제 AI 결과일 때만 표시한다.
        if (results[2].status === "fulfilled" &&
            results[1].status === "fulfilled") {
          setCleanEdges(results[2].value.features);
          setDataSource("model-csv");
          setRisks(results[1].value);
        } else {
          if (results[2].status === "rejected") {
            console.error(results[2].reason);
          }
          if (results[1].status === "rejected") {
            console.error(results[1].reason);
          }
          setCleanEdges([]);
          setRisks([]);
          setDataSource(null);
          setError("AI 모델 결과를 불러오지 못했습니다. 백엔드의 LUNG_RISK_CSV 설정과 모델 CSV를 확인하세요.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  // 로그인 후에는 전체 신고,
  // 로그인 전에는 승인된 공개 신고만 표시
  const visibleReports =
    adminReports ?? publicReports;

  // 관리자 신고 위치로 지도 이동
  function focusReportLocation(point: Coordinate) {
    setFocusPoint([...point]);
    setShowReports(true);
  }

  // 관리자 검토 완료 후 공개 신고 목록 갱신
  async function handleReviewCompleted() {
    await refreshPublicReports();
  }

  return (
    <div className="flex h-full flex-col bg-white">
      {/* B2G 헤더 */}
      <header className="z-[1000] bg-white px-5 py-4 shadow-sm">
        <h1 className="pr-44 text-xl font-bold text-slate-800">
          숨구리당당
        </h1>

        <p className="mt-1 text-xs text-gray-500">
          B2G · 강남구 흡연 위험 분석 및 신고 관리
        </p>
      </header>

      {/* Header admin control: left of the existing service selector in App.tsx. */}
      <div className="absolute right-[4.25rem] top-3 z-[1201] flex items-center gap-2">
        <button type="button"
          onClick={() => {
            if (adminAuthorized) {
              setLogoutSignal(value => value + 1);
              setShowAdminPanel(false);
            } else {
              setShowAdminPanel(value => !value);
            }
          }}
          aria-expanded={!adminAuthorized ? showAdminPanel : undefined}
          className="flex h-10 items-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 shadow">
          {adminAuthorized ? "관리자 로그아웃" : "관리자 로그인"}
        </button>
      </div>

      {/* Keep authentication mounted while the independent panel is closed. */}
      <aside aria-label="관리자 인증 및 신고 관리"
        className={`absolute right-3 top-16 z-[1100] max-h-[min(72dvh,calc(100%-5rem))] w-[min(420px,calc(100%-24px))] overflow-y-auto rounded-2xl border bg-white p-4 shadow-xl ${showAdminPanel ? "" : "hidden"}`}>
        <div className="mb-3 flex justify-end">
          <button type="button" onClick={() => setShowAdminPanel(false)}
            aria-label="관리자 창 닫기" className="rounded-lg border px-3 py-1 text-sm">닫기 ×</button>
        </div>
        {adminAuthorized && (
          <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
            <p className="font-bold">관리자 로그인 완료</p>
            <p className="mt-1 text-xs">지자체 분석 패널에서 관리자 대시보드, DBSCAN 입지 추천, 어린이집 보호 우선순위를 이용할 수 있습니다.</p>
            <p className="mt-2 text-xs">관리자 창을 닫아도 상단의 ‘지자체 분석’ 메뉴에서 분석을 확인할 수 있습니다.</p>
          </div>
        )}
        <AdminDashboard
          dashboardTarget={dashboardTarget}
          riskSource={dataSource}
          onSessionChange={handleSessionChange}
          reports={publicReports}
          risks={risks}
          onFocusLocation={focusReportLocation}
          onReviewCompleted={handleReviewCompleted}
          onAdminReportsChange={setAdminReports}
          onAuthorizedChange={(value) => {
            setAdminAuthorized(value);
            if (value) {
              // Enter submits the login form; successful authentication must not
              // unexpectedly dismiss the dialog. The user closes it explicitly.
              setShowAdminPanel(true);
              setShowDashboard(true);
              setAnalysisTab("reports");
            } else {
              // An incorrect password also reports unauthorized. Keep the
              // login form visible so Enter does not make it disappear.
              // Actual logout from an authenticated session can close it.
              if (adminAuthorized) setShowAdminPanel(false);
              setShowDashboard(false);
              setDashboardTarget(null);
            }
          }}
          logoutSignal={logoutSignal}
        />
      </aside>

      {/* B2G: analysis navigation stays outside the map, immediately beneath the header. */}
      <main className="flex min-h-0 flex-1 flex-col">
        {adminAuthorized && (
          <nav aria-label="지자체 분석 메뉴" className="z-[900] flex shrink-0 items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
            <div role="tablist" aria-label="지자체 분석 탭" className="flex min-w-0 flex-wrap gap-1">
              {([
                ["reports", "관리자 대시보드"],
                ["childcare", "어린이집 보호 우선순위"],
                ["dbscan", "DBSCAN 입지 추천"],
              ] as const).map(([tab, label]) => (
                <button key={tab} type="button" role="tab"
                  aria-selected={showDashboard && analysisTab === tab}
                  onClick={() => { selectAnalysisTab(tab); setShowDashboard(true); }}
                  className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 sm:text-sm ${showDashboard && analysisTab === tab ? "bg-teal-100 text-teal-900" : "text-slate-700 hover:bg-slate-100"}`}>
                  {label}
                </button>
              ))}
            </div>
            <button type="button" onClick={() => setShowDashboard(value => !value)}
              aria-expanded={showDashboard}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
              {showDashboard ? "패널 접기" : "패널 열기"}
            </button>
          </nav>
        )}

        <div className="flex min-h-0 flex-1">
          {adminAuthorized && showDashboard && (
            <aside aria-label="지자체 분석" className="h-full w-[min(380px,46vw)] shrink-0 overflow-y-auto overscroll-contain border-r border-slate-200 bg-white p-3 max-[640px]:w-[min(310px,70vw)]">
              <div className="mb-3 border-b border-slate-100 pb-3">
                <h2 className="text-base font-bold text-slate-800">지자체 분석</h2>
                <p className="mt-1 text-xs leading-4 text-slate-500">
                  관리자 제보 검토 · 흡연시설 입지 추천 · 어린이집 보호 우선순위
                </p>
              </div>
              {analysisTab === "reports" ? (
                <div role="tabpanel" aria-label="관리자 대시보드" ref={setDashboardTarget} />
              ) : analysisTab === "dbscan" ? (
                <div role="tabpanel" aria-label="DBSCAN 입지 추천">
                  <DbscanSitePanel
                    data={dbscanSites}
                    loading={dbscanLoading}
                    error={dbscanError}
                    selectedCluster={selectedDbscanCluster ?? ""}
                    onClusterChange={setSelectedDbscanCluster}
                    onFocus={focusDbscanCandidate}
                    onReload={() => void loadDbscanSites()}
                  />
                </div>
              ) : (
                <div role="tabpanel" aria-label="어린이집 보호 우선순위">
                  <ChildcareExposurePanel
                    data={childcareData}
                    loading={childcareLoading}
                    error={childcareError}
                    onReload={() => void loadChildcareExposure()}
                    onFocus={focusChildcare}
                  />
                </div>
              )}
            </aside>
          )}

          {/* The map uses the remaining width rather than sitting beneath the analysis panel. */}
          <div className="relative min-w-0 flex-1">
            <MapView
              audience="b2g"
              start={null}
              end={null}
              routes={[]}
              risks={risks}
              cleanlinessEdges={cleanEdges}
              dbscanSites={dbscanSites}
              showDbscanSites={adminAuthorized && analysisTab === "dbscan" && dbscanSites !== null}
              selectedDbscanCluster={selectedDbscanCluster ?? ""}
              selectedChildcare={adminAuthorized && analysisTab === "childcare" ? selectedChildcare : null}
              reports={visibleReports}
              showRisks={showRisks}
              showReports={showReports}
              onToggleCleanliness={() => setShowRisks(value => !value)}
              onToggleReports={() => setShowReports(value => !value)}
              reportLocation={null}
              focusPoint={focusPoint}
              onMapClick={() => {
                // B2G는 지도 클릭으로 경로 및 신고 위치를 입력하지 않음
              }}
            />
            {showRisks && cleanEdges.length > 0 && <CleanlinessLegend scope="network" />}
          </div>
        </div>
      </main>

    </div>
  );
}
