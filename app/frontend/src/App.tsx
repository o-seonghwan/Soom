
import { useEffect, useState } from "react";

import B2CApp from "./B2CApp";
import B2GDashboard from "./B2GDashboard";

type ServiceMode = "b2c" | "b2g" | null;

export default function App() {
  const [serviceMode, setServiceMode] =
    useState<ServiceMode>(null);
  const [isMobile, setIsMobile] = useState(() => window.matchMedia("(max-width: 760px)").matches);
  // Only the first mobile app entry shows the splash; returning to service selection does not.
  const [showMobileSplash, setShowMobileSplash] = useState(
    () => window.matchMedia("(max-width: 760px)").matches
  );

  useEffect(() => {
    if (!showMobileSplash) return;
    const timer = window.setTimeout(() => setShowMobileSplash(false), 2000);
    return () => window.clearTimeout(timer);
  }, [showMobileSplash]);


  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const update = () => setIsMobile(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  // Display the provided artwork for two seconds on initial mobile entry.
  if (showMobileSplash && isMobile) {
    return (
      <main
        aria-label="숨길 시작 화면"
        className="fixed inset-0 flex h-dvh w-full items-center justify-center overflow-hidden"
        style={{ backgroundColor: "#ecfaf4" }}
      >
        <img
          src="/soom-mobile-splash.webp"
          alt="숨길의 수미, 구리, 당당 캐릭터가 위치 아이콘 주변에 모인 시작 화면"
          className="h-full w-full object-contain"
          fetchPriority="high"
        />
      </main>
    );
  }

  // 최초 서비스 선택 화면
  if (serviceMode === null) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-green-50 px-5 py-10">
        <div className="w-full max-w-4xl">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-green-800">
              숨길
            </h1>

            <p className="mt-3 text-gray-600">
              이용할 서비스를 선택해주세요.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            {/* B2C 일반 사용자 */}
            <button
              type="button"
              onClick={() => setServiceMode("b2c")}
              className="rounded-2xl border-2 border-green-200 bg-white p-8 text-left shadow-sm transition hover:border-green-500 hover:shadow-md"
            >
              <p className="text-sm font-bold text-green-700">
                B2C · 일반 사용자
              </p>

              <h2 className="mt-4 text-2xl font-bold text-gray-900">
                청정 경로 찾기
              </h2>
              <p className="mt-2 text-sm font-semibold text-green-700">숨편하게, 맘편하게</p>

              <p className="mt-4 text-sm leading-7 text-gray-600">
                간접흡연 위험을 고려한 보행 경로를
                탐색하고, 흡연 관련 상황을
                제보할 수 있습니다.
              </p>

              <div className="mt-6 rounded-lg bg-green-50 px-4 py-3 text-sm font-semibold text-green-700">
                사용자 서비스로 입장
              </div>
            </button>

            {/* B2G 지자체 */}
            <button
              type="button"
              onClick={() => { if (!isMobile) setServiceMode("b2g"); }}
              disabled={isMobile}
              aria-label={isMobile ? "지자체 서비스는 데스크톱에서 이용할 수 있습니다" : "지자체 서비스로 입장"}
              className="rounded-2xl border-2 border-slate-200 bg-white p-8 text-left shadow-sm transition hover:border-slate-500 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
            >
              <p className="text-sm font-bold text-slate-600">
                B2G · 지자체 및 관리자
              </p>

              <h2 className="mt-4 text-2xl font-bold text-gray-900">
                흡연 위험 현황 분석
              </h2>
              <p className="mt-2 text-sm font-semibold text-slate-600">간편하게</p>

              <p className="mt-4 text-sm leading-7 text-gray-600">
                신고 현황을 검토하고,
                위험지역과 DBSCAN 군집 분석 결과를
                확인하는 관리 서비스입니다.
              </p>

              <div className="mt-6 rounded-lg bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">
                {isMobile ? "모바일에서는 이용할 수 없습니다 · PC에서 접속해주세요" : "지자체 서비스로 입장"}
              </div>
            </button>
          </div>

          <p className="mt-6 text-center text-xs text-gray-500">
            현재 강남구 기반 프로토타입입니다.
          </p>
        </div>
      </main>
    );
  }

  // 서비스 화면
  return (
    <div className="relative h-dvh">
      <button
        type="button"
        onClick={() => setServiceMode(null)}
        aria-label="서비스 다시 선택"
        title="서비스 다시 선택"
        className={`absolute right-3 top-3 z-[1200] flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-xl font-bold text-gray-700 shadow hover:bg-gray-50 ${serviceMode === "b2c" ? "max-[760px]:left-3 max-[760px]:right-auto max-[760px]:top-[136px] max-[760px]:h-9 max-[760px]:w-9" : ""}`}
      >
        ×
      </button>

      {serviceMode === "b2c" ? (
        <B2CApp />
      ) : isMobile ? (
        <main className="flex h-full items-center justify-center bg-slate-50 px-6 text-center">
          <div className="max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h1 className="text-xl font-bold text-slate-800">숨길 B2G · 모바일 이용 제한</h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              관리자 대시보드는 넓은 화면이 필요합니다. 데스크톱에서 이용해주세요.
            </p>
          </div>
        </main>
      ) : (
        <B2GDashboard />
      )}
    </div>
  );
}
