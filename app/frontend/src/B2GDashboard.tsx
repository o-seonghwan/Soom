
import { useCallback, useEffect, useState } from "react";

import MapView from "./components/MapView";
import AdminDashboard from "./components/AdminDashboard";
import { getB2GCleanEdges } from "./services/cleanlinessService";
import type { CleanEdgeFeature } from "./types/cleanliness";
import { getCleanColor } from "./utils/cleanColor";

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
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [adminAuthorized, setAdminAuthorized] = useState(false);
  const [logoutSignal, setLogoutSignal] = useState(0);

  const [focusPoint, setFocusPoint] =
    useState<Coordinate | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

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
        {adminAuthorized && (
          <button type="button" onClick={() => setShowAdminPanel(value => !value)}
            aria-expanded={showAdminPanel}
            className="flex h-10 items-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 shadow">
            관리자 관리
          </button>
        )}
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
        <AdminDashboard
          reports={publicReports}
          risks={risks}
          onFocusLocation={focusReportLocation}
          onReviewCompleted={handleReviewCompleted}
          onAdminReportsChange={setAdminReports}
          onAuthorizedChange={(value) => { setAdminAuthorized(value); if (value) setShowAdminPanel(true); }}
          logoutSignal={logoutSignal}
        />
      </aside>

      {/* B2G 지도 */}
      <main className="relative min-h-0 flex-1">
        <MapView
          audience="b2g"
          start={null}
          end={null}
          routes={[]}
          risks={risks}
          cleanlinessEdges={cleanEdges}
          reports={visibleReports}
          showRisks={showRisks}
          showReports={showReports}
          onToggleCleanliness={() => setShowRisks(value => !value)}
          onToggleReports={() => setShowReports(value => !value)}
          reportLocation={null}
          focusPoint={focusPoint}
          onMapClick={() => {
            // B2G는 지도 클릭으로
            // 경로 및 신고 위치를 입력하지 않음
          }}
        />

        {showRisks && cleanEdges.length > 0 && (
          <div className="absolute bottom-14 left-3 z-[500] rounded-xl bg-white/95 p-3 shadow-lg">
            <h3 className="text-sm font-bold">보행로 청정지수 · AI 모델</h3>
            <div className="mt-2 flex gap-2 text-xs">
              {[{n: 10,t: "0–19"}, {n: 30,t: "20–39"}, {n: 50,t: "40–59"}, {n: 70,t: "60–79"}, {n: 90,t: "80–100"}].map(({n,t}) => (
                <div key={n} className="flex flex-col items-center gap-1">
                  <span className="h-3 w-8 rounded" style={{background: getCleanColor(n)}}/>
                  <span>{t}</span>
                </div>
              ))}
            </div>
            <p className="mt-2 max-w-72 text-[10px] text-gray-600">높을수록 상대적으로 청정 · 비표시 구간은 데이터 없음 · 실측 대기질이 아님</p>
          </div>
        )}
        {/* Independent collapsible B2G analysis dashboard */}
              <button type="button" onClick={() => setShowDashboard(value => !value)}
                aria-expanded={showDashboard}
                className="absolute top-3 left-3 z-[1050] rounded-xl border border-slate-200 bg-white/95 px-4 py-2 text-sm font-bold text-slate-700 shadow-lg">
                {showDashboard ? "지자체 분석 대시보드 닫기 ×" : "지자체 분석 대시보드 ☰"}
              </button>
        
      </main>

      {showDashboard && (
      <section className="z-[1000] max-h-[55dvh] space-y-4 overflow-y-auto bg-white p-4 pb-16 shadow-lg">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            지자체 분석 대시보드
          </h2>

          <p className="mt-1 text-xs text-gray-500">
            위험지역, 신고 데이터 및 분석 결과
          </p>
        </div>

        {/* 현재 데이터 현황 */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border p-4">
            <p className="text-xs text-gray-500">
              지도에 표시할 신고
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-800">
              {visibleReports.length}
              <span className="ml-1 text-sm font-normal">
                건
              </span>
            </p>

            <p className="mt-1 text-xs text-gray-500">
              {adminReports
                ? "관리자 전체 신고 기준"
                : "승인된 공개 신고 기준"}
            </p>
          </div>

          <div className="rounded-xl border p-4">
            <p className="text-xs text-gray-500">
              위험 지점 데이터
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-800">
              {risks.length}
              <span className="ml-1 text-sm font-normal">
                개
              </span>
            </p>

            <p className="mt-1 text-xs text-gray-500">
              {dataSource === "model-csv" ? "실제 모델 위험점수 기반" : "AI 모델 연결 안 됨"}
            </p>
          </div>
        </div>

        {loading && (
          <p className="text-sm text-gray-500">
            지도 데이터를 불러오는 중...
          </p>
        )}

        {error && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
          >
            {error}
          </p>
        )}

        {/* DBSCAN: 실제 결과 연결 전 */}
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-bold text-slate-800">
              DBSCAN 군집 분석
            </h3>

            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
              연동 준비
            </span>
          </div>

          <p className="mt-3 text-sm text-gray-600">
            현재 DBSCAN 분석 결과 API는
            연결되지 않았습니다.
          </p>

          <p className="mt-2 text-xs leading-6 text-gray-500">
            향후 군집별 신고 건수, 군집 중심,
            공간적 분포, 노이즈 지점 및
            밀집지역 분석 결과를 이 영역과
            지도에 표시할 예정입니다.
          </p>
        </div>

        <p className="text-xs leading-5 text-gray-500">
          관리자 로그인 전에는 승인된 공개 신고만
          지도에 표시됩니다. 로그인 후에는
          관리자 권한으로 조회한 신고 전체를
          표시합니다. 청정지수는 위험점수 기반 파생값이며
          DBSCAN 분석은 아직 연결되지 않았습니다.
        </p>
      </section>
      )}
    </div>
  );
}
