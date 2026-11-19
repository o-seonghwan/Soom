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
    <section aria-label="어린이집 보호 우선순위" className="space-y-4">
      <header>
        <h3 className="text-lg font-bold text-slate-900">어린이집 보호 우선순위</h3>
        <p className="mt-1 text-xs leading-5 text-slate-600">
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
            <div className="rounded-xl bg-violet-50 p-3">
              <p className="text-xs font-semibold text-violet-900">분석 어린이집</p>
              <p className="mt-1 text-2xl font-bold text-violet-950">{fmt(data.summary.nurseryCount)}곳</p>
            </div>
            <div className="rounded-xl bg-violet-50 p-3">
              <p className="text-xs font-semibold text-violet-900">상위 10% 위험지점 인접</p>
              <p className="mt-1 text-2xl font-bold text-violet-950">{fmt(data.summary.withHighRiskPoints)}곳</p>
            </div>
          </div>
          <div>
            <label htmlFor="childcare-search" className="mb-1 block text-sm font-bold text-slate-700">
              어린이집 이름 또는 주소 검색
            </label>
            <input id="childcare-search" type="search" value={query} onChange={event => setQuery(event.target.value)}
              placeholder="어린이집 검색" className="w-full rounded-lg border border-slate-300 p-2 text-sm" />
            <label className="mt-3 flex items-center gap-2 text-xs text-slate-700">
              <input type="checkbox" checked={onlyHighRisk}
                onChange={event => setOnlyHighRisk(event.target.checked)} />
              위험 상위 10% 보행 지점이 인접한 어린이집만
            </label>
            <p className="mt-2 text-xs text-slate-500">표시 {fmt(nurseries.length)}곳 · 우선순위 순</p>
          </div>
          <div className="max-h-[45dvh] space-y-3 overflow-y-auto pr-1">
            {nurseries.map(nursery => (
              <article key={nursery.id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-bold text-violet-800">보호 우선순위 {nursery.priorityRank}위</p>
                    <h4 className="mt-1 font-bold text-slate-900">{nursery.name}</h4>
                    <p className="mt-1 text-xs text-slate-600">{nursery.address}</p>
                  </div>
                  <span className="shrink-0 rounded-lg bg-violet-100 px-2 py-1 text-sm font-bold text-violet-900">
                    {point(nursery.exposureScore)}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">{nursery.type} · 현원 {fmt(nursery.enrollment)}명</p>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-slate-50 p-2"><dt>주변 최고 위험점수</dt><dd className="mt-1 font-bold">{point(nursery.nearbyMaxRisk)}</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt>주변 평균 위험점수</dt><dd className="mt-1 font-bold">{point(nursery.nearbyMeanRisk)}</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt>주변 보행 분석지점</dt><dd className="mt-1 font-bold">{fmt(nursery.nearbyPointCount)}곳</dd></div>
                  <div className="rounded-lg bg-slate-50 p-2"><dt>위험 상위 10% 지점</dt><dd className="mt-1 font-bold">{fmt(nursery.highRiskPointCount)}곳</dd></div>
                </dl>
                <button type="button" onClick={() => onFocus(nursery)}
                  className="mt-3 w-full rounded-lg bg-violet-700 px-3 py-2 text-xs font-bold text-white">
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
