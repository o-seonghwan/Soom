
import { useState } from "react";

import B2CApp from "./B2CApp";
import B2GDashboard from "./B2GDashboard";

type ServiceMode = "b2c" | "b2g" | null;

export default function App() {
  const [serviceMode, setServiceMode] =
    useState<ServiceMode>(null);

  // 최초 서비스 선택 화면
  if (serviceMode === null) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-green-50 px-5 py-10">
        <div className="w-full max-w-4xl">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-green-800">
              숨구리당당
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
              onClick={() => setServiceMode("b2g")}
              className="rounded-2xl border-2 border-slate-200 bg-white p-8 text-left shadow-sm transition hover:border-slate-500 hover:shadow-md"
            >
              <p className="text-sm font-bold text-slate-600">
                B2G · 지자체 및 관리자
              </p>

              <h2 className="mt-4 text-2xl font-bold text-gray-900">
                흡연 위험 현황 분석
              </h2>

              <p className="mt-4 text-sm leading-7 text-gray-600">
                신고 현황을 검토하고,
                위험지역과 DBSCAN 군집 분석 결과를
                확인하는 관리 서비스입니다.
              </p>

              <div className="mt-6 rounded-lg bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">
                지자체 서비스로 입장
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
        className="absolute right-3 top-3 z-[1200] flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-white text-xl font-bold text-gray-700 shadow hover:bg-gray-50"
      >
        ×
      </button>

      {serviceMode === "b2c" ? (
        <B2CApp />
      ) : (
        <B2GDashboard />
      )}
    </div>
  );
}
