import { useState } from "react";
import type { ChildcareExposure, ChildcareExposureResponse } from "../types/childcare";

interface Props {
  data: ChildcareExposureResponse | null;
  loading: boolean;
  error: string;
  onReload: () => void;
  onFocus: (nursery: ChildcareExposure) => void;
}

const point = (value: number | null) => value === null ? "산정 불가" : value.toFixed(1);
const fmt = (value: number) => value.toLocaleString("ko-KR");

export default function ChildcareExposurePanel({ data, loading, error, onReload, onFocus }: Props) {
  const [query, setQuery] = useState("");
  const [onlyHighRisk, setOnlyHighRisk] = useState(false);
  const nurseries = data?.nurseries.filter(n =>
    (!onlyHighRisk || n.highRiskPointCount > 0) &&
    (`${n.name} ${n.address}`.toLowerCase().includes(query.trim().toLowerCase()))
  ) ?? [];

  return (
    <section aria-label="어린이집 보호 우선순위" className="space-y-3">
      <header>
        <h3 className="text-base font-bold text-slate-900">어린이집 보호 우선순위</h3>
        <p className="mt-1 text-[11px] leading-4 text-slate-500">
          어린이집 주변 반경 100m의 AI 보행 위험지수로 산정한 우선순위입니다.
        </p>
      </header>
      {loading && <p role="status" className="text-sm">어린이집 노출순위를 불러오는 중...</p>}
      {error && (
        <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
          <p>{error}</p>
          <button type="button" onClick={onReload}
            className="mt-3 rounded-lg border border-amber-400 px-3 py-2 font-semibold">다시 불러오기</button>
        </div>
      )}
      {data && !loading && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-2.5">
              <p className="text-[11px] font-semibold text-teal-900">분석 어린이집</p>
              <p className="mt-1 text-2xl font-extrabold tracking-tight text-slate-800">{fmt(data.summary.nurseryCount)}<span className="ml-0.5 text-xs font-semibold text-slate-600">곳</span></p>
            </div>
            <div className="rounded-xl bg-violet-50 p-3">
              <p className="text-[11px] font-semibold text-teal-900">상위 10% 위험지점 인접</p>
              <p className="mt-1 text-2xl font-extrabold tracking-tight text-slate-800">{fmt(data.summary.withHighRiskPoints)}<span className="ml-0.5 text-xs font-semibold text-slate-600">곳</span></p>
            </div>
          </div>
          <div>
            <label htmlFor="childcare-search" className="sr-only">
              어린이집 이름 또는 주소 검색
            </label>
            <input id="childcare-search" type="search" value={query} onChange={event => setQuery(event.target.value)}
              placeholder="어린이집 검색" className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-100" />
            <label className="mt-2 flex items-center gap-2 text-[11px] text-slate-700">
              <input type="checkbox" checked={onlyHighRisk}
                onChange={event => setOnlyHighRisk(event.target.checked)} />
              위험 상위 10% 보행 지점이 인접한 어린이집만
            </label>
            <p className="mt-1 text-[11px] text-slate-500">표시 {fmt(nurseries.length)}곳 · 우선순위 순</p>
          </div>
          <div className="min-h-[180px] space-y-2.5 pr-1" style={{ overflowAnchor: "none" }}>
            {nurseries.map(nursery => (
              <article key={nursery.id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-bold text-teal-700">보호 우선순위 {nursery.priorityRank}위</p>
                    <h4 className="mt-1 text-sm font-bold text-slate-900">{nursery.name}</h4>
                    <p className="mt-1 text-[11px] leading-4 text-slate-600">{nursery.address}</p>
                  </div>
                  <span className={`shrink-0 rounded-lg px-2 py-1 text-sm font-extrabold text-white ${nursery.nearbyPointCount === 0 ? "bg-slate-500" : nursery.exposureScore >= 90 ? "bg-rose-600" : nursery.exposureScore >= 70 ? "bg-orange-500" : "bg-teal-600"}`}>
                    {nursery.nearbyPointCount > 0 ? point(nursery.exposureScore) : "지점 없음"}
                  </span>
                </div>
                <p className="mt-2 text-[11px] text-slate-500">{nursery.type} · 현원 {fmt(nursery.enrollment)}명</p>
                {nursery.nearbyPointCount === 0 && (
                  <p className="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-900">
                    100m 내 분석 보행 지점이 없어 위험도를 평가할 수 없습니다. 원본 CSV의 노출점수 0은 안전 판정이 아닙니다.
                  </p>
                )}
                <dl className="mt-2 grid grid-cols-2 gap-1.5 text-[11px]">
                  <div className="rounded-lg bg-teal-50 p-2"><dt className="text-[10px] text-slate-700">주변 최고 위험점수</dt><dd className="mt-1 text-lg font-extrabold text-rose-600">{point(nursery.nearbyMaxRisk)}<span className="ml-0.5 text-[10px] font-medium text-slate-600">점</span></dd></div>
                  <div className="rounded-lg bg-teal-50 p-2"><dt className="text-[10px] text-slate-700">주변 평균 위험점수</dt><dd className="mt-1 text-lg font-extrabold text-rose-600">{point(nursery.nearbyMeanRisk)}<span className="ml-0.5 text-[10px] font-medium text-slate-600">점</span></dd></div>
                  <div className="rounded-lg bg-teal-50 p-2"><dt className="text-[10px] text-slate-700">주변 보행 분석지점</dt><dd className="mt-1 text-lg font-extrabold text-teal-700">{fmt(nursery.nearbyPointCount)}<span className="ml-0.5 text-[10px] font-medium text-slate-600">곳</span></dd></div>
                  <div className="rounded-lg bg-teal-50 p-2"><dt className="text-[10px] text-slate-700">위험 상위 10% 지점</dt><dd className="mt-1 text-lg font-extrabold text-rose-600">{fmt(nursery.highRiskPointCount)}<span className="ml-0.5 text-[10px] font-medium text-slate-600">곳</span></dd></div>
                </dl>
                <button type="button" onClick={() => onFocus(nursery)}
                  className="mt-3 w-full rounded-lg bg-teal-500 px-3 py-2 text-xs font-bold text-slate-950 transition-colors hover:bg-teal-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700">
                  지도에서 위치 확인
                </button>
              </article>
            ))}
            {nurseries.length === 0 && <p className="rounded-lg bg-slate-50 p-3 text-sm">조건에 맞는 어린이집이 없습니다.</p>}
          </div>
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
            {data.disclaimer}
          </p>
          <p className="text-xs text-slate-500">
            노출점수 = (주변 최고 위험점수 + 주변 평균 위험점수) / 2.
            노출점수 내림차순이며 동점이면 같은 우선순위가 부여됩니다.
            보행 지점이 없는 시설은 원본 분석에서 결측 점수를 0으로 처리합니다.
          </p>
        </>
      )}
    </section>
  );
}
