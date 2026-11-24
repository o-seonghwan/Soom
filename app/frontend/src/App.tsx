
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
          className="h-full w-full scale-[1.3] object-contain"
          fetchPriority="high"
        />
      </main>
    );
  }

  // 서비스 선택: 데스크톱은 제공된 2열 레이아웃, 모바일은 세로형 카드 배치.
  if (serviceMode === null) {
    return (
      <main
        className="min-h-dvh overflow-y-auto px-4 pb-12 pt-[min(11dvh,100px)] sm:px-6 min-[761px]:pt-[min(22dvh,220px)]"
        style={{
          background:
            "radial-gradient(ellipse at 50% 44%, #ffffff 0%, #f7fffc 43%, #e9fcf5 100%)",
        }}
      >
        <div className="mx-auto w-full max-w-[970px]">
          <header className="mb-4 flex w-full items-center justify-between gap-3 min-[761px]:grid min-[761px]:grid-cols-[1fr_auto_1fr] min-[761px]:gap-0">
            <div className="flex shrink-0 items-center gap-2 min-[761px]:col-start-2 min-[761px]:justify-self-center" aria-label="숨길">
              <svg width="43" height="60" viewBox="0 0 46 64" role="img" aria-label="숨길 위치 로고" className="h-[50px] w-[36px] min-[761px]:h-[60px] min-[761px]:w-[43px]">
                <defs>
                  <linearGradient id="soomPinGradient" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0" stopColor="#8AFBE1" />
                    <stop offset="0.54" stopColor="#40DDB8" />
                    <stop offset="1" stopColor="#18A985" />
                  </linearGradient>
                </defs>
                <ellipse cx="23" cy="60" rx="10" ry="2.5" fill="#164E3C" opacity="0.13" />
                <path d="M23 2C11 2 3 12 3 24c0 15 20 35 20 35s20-20 20-35C43 12 35 2 23 2Z" fill="url(#soomPinGradient)" />
                <ellipse cx="17" cy="12" rx="8" ry="3.5" transform="rotate(-28 17 12)" fill="#fff" opacity="0.32" />
                <text x="23" y="35" textAnchor="middle" fontSize="27" fontWeight="800" fontFamily="Arial, sans-serif" fontStyle="italic" fill="white">S</text>
              </svg>
              <h1 className="whitespace-nowrap text-[31px] font-extrabold tracking-[-0.05em] text-[#08783D] min-[761px]:text-[36px]">
                숨길
              </h1>
            </div>
            <img
              src="/soom-service-mascots.webp"
              alt="손을 잡고 인사하는 수미, 구리, 당당"
              className="h-auto w-[min(57%,255px)] shrink object-contain min-[761px]:col-start-3 min-[761px]:w-[264px] min-[761px]:justify-self-end"
            />
          </header>

          <div className="grid grid-cols-1 items-stretch gap-5 min-[761px]:grid-cols-2 min-[761px]:gap-6">
            <button
              type="button"
              onClick={() => setServiceMode("b2c")}
              className="flex min-h-[315px] w-full flex-col rounded-[20px] border-2 border-[#ADEDD0] bg-white px-6 py-7 text-left shadow-[0_3px_7px_rgba(20,110,78,0.08)] transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-700 min-[761px]:min-h-[326px] min-[761px]:px-8 min-[761px]:py-8"
            >
              <p className="text-[13px] font-bold text-[#08783D]">B2C · 일반 사용자</p>
              <h2 className="mt-4 text-[25px] font-extrabold leading-tight text-[#181818]">
                청정 경로 찾기
              </h2>
              <p className="mt-3 text-[14px] font-bold text-[#08783D]">숨편하게, 맘편하게</p>
              <p className="mt-5 text-[13px] leading-[1.9] text-[#555]">
                간접흡연 위험을 고려한 보행 경로를 탐색하고,
                흡연 관련 상황을 제보할 수 있습니다.
              </p>
              <div className="mt-auto w-full rounded-lg bg-[#EAF8EF] px-4 py-4 text-[13px] font-bold text-[#08783D]">
                사용자 서비스로 입장
              </div>
            </button>

            <button
              type="button"
              onClick={() => { if (!isMobile) setServiceMode("b2g"); }}
              disabled={isMobile}
              aria-label={isMobile ? "지자체 서비스는 데스크톱에서 이용할 수 있습니다" : "지자체 서비스로 입장"}
              className="flex min-h-[315px] w-full flex-col rounded-[20px] border-2 border-[#DFE3EA] bg-white px-6 py-7 text-left shadow-[0_3px_7px_rgba(31,41,55,0.08)] transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700 disabled:cursor-not-allowed min-[761px]:min-h-[326px] min-[761px]:px-8 min-[761px]:py-8"
            >
              <p className="text-[13px] font-bold text-[#293B54]">B2G · 지자체 및 관리자</p>
              <h2 className="mt-4 text-[25px] font-extrabold leading-tight text-[#181818]">
                흡연 위험 현황 분석
              </h2>
              <p className="mt-3 text-[14px] font-bold text-[#293B54]">간편하게</p>
              <p className="mt-5 text-[13px] leading-[1.9] text-[#555]">
                신고 현황을 검토하고, 위험지역과 DBSCAN 군집 분석 결과를
                확인하는 관리 서비스입니다.
              </p>
              <div className="mt-auto w-full rounded-lg bg-[#F0F3F7] px-4 py-4 text-[13px] font-bold text-[#293B54]">
                {isMobile ? "PC에서 이용할 수 있습니다" : "지자체 서비스로 입장"}
              </div>
            </button>
          </div>
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
