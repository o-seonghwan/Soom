
import { useCallback, useEffect, useState } from "react";

import MapView from "./components/MapView";
import AdminDashboard from "./components/AdminDashboard";
import RiskLegend from "./components/RiskLegend";

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

  // 지도 표시 옵션
  const [showReports, setShowReports] =
    useState(true);

  const [showRisks, setShowRisks] =
    useState(true);

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

        if (results[1].status === "fulfilled") {
          setRisks(results[1].value);
        } else {
          console.error(results[1].reason);
          setError(
            "위험도 데이터를 불러오지 못했습니다."
          );
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
          폐(Lung) 끼치지 마세요
        </h1>

        <p className="mt-1 text-xs text-gray-500">
          B2G · 강남구 흡연 위험 분석 및 신고 관리
        </p>
      </header>

      {/* B2G 지도 */}
      <main className="relative min-h-0 flex-1">
        <MapView
          start={null}
          end={null}
          routes={[]}
          risks={risks}
          reports={visibleReports}
          showRisks={showRisks}
          showReports={showReports}
          reportLocation={null}
          focusPoint={focusPoint}
          onMapClick={() => {
            // B2G는 지도 클릭으로
            // 경로 및 신고 위치를 입력하지 않음
          }}
        />

        {showRisks && risks.length > 0 && (
          <RiskLegend />
        )}
      </main>

      {/* B2G 하단 분석 패널 */}
      <section className="z-[1000] max-h-[55dvh] space-y-4 overflow-y-auto bg-white p-4 shadow-lg">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            지자체 분석 대시보드
          </h2>

          <p className="mt-1 text-xs text-gray-500">
            위험지역, 신고 데이터 및 분석 결과
          </p>
        </div>

        {/* 지도 표시 설정 */}
        <div className="flex flex-wrap gap-5 rounded-lg bg-slate-50 p-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showReports}
              onChange={(event) =>
                setShowReports(event.target.checked)
              }
              className="h-4 w-4 accent-purple-600"
            />
            신고 위치 표시 ({visibleReports.length}건)
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showRisks}
              onChange={(event) =>
                setShowRisks(event.target.checked)
              }
              className="h-4 w-4 accent-slate-600"
            />
            위험지역 표시
          </label>
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
              현재 Mock 위험 데이터
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

        {/* 기존 관리자 신고 관리 재사용 */}
        <div className="rounded-xl border border-slate-200 p-4">
          <AdminDashboard
            reports={publicReports}
            risks={risks}
            onFocusLocation={focusReportLocation}
            onReviewCompleted={handleReviewCompleted}
            onAdminReportsChange={setAdminReports}
          />
        </div>

        <p className="text-xs leading-5 text-gray-500">
          관리자 로그인 전에는 승인된 공개 신고만
          지도에 표시됩니다. 로그인 후에는
          관리자 권한으로 조회한 신고 전체를
          표시합니다. 현재 위험 데이터는 Mock이며
          DBSCAN 분석은 아직 연결되지 않았습니다.
        </p>
      </section>
    </div>
  );
}
