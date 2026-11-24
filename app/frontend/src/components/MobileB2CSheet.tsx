import { useState, type ReactNode } from "react";
import type { Route, RouteRequest } from "../types/route";
import CleanlinessLegend from "./CleanlinessLegend";
import RoutePanel from "./RoutePanel";

type MobileTab = "shortest" | "safest" | "report";

interface Props {
  pageMode: MobileTab;
  onTabChange: (mode: MobileTab) => void;
  routes: Route[];
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange: (level: RouteRequest["avoidanceLevel"]) => void;
  loading: boolean;
  elapsedSeconds: number;
  searchError: boolean;
  reportContent: ReactNode;
  reportError: string | null;
}

/** Mobile-only B2C sheet; the desktop result panel remains independent. */
export default function MobileB2CSheet({
  pageMode, onTabChange, routes, avoidanceLevel, onAvoidanceLevelChange,
  loading, elapsedSeconds, searchError, reportContent, reportError,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const shortest = routes.find(route => route.id === "shortest");
  const safest = routes.find(route => route.id === "safest");
  const active = pageMode === "shortest" ? shortest : safest;

  // Unknown links are excluded. This is a relative model-derived index,
  // not a measured air quality or smoke exposure probability.
  function lengthM(coordinates: [number, number][]) {
    let total = 0;
    for (let i = 1; i < coordinates.length; i++) {
      const [latA, lngA] = coordinates[i - 1];
      const [latB, lngB] = coordinates[i];
      const radians = Math.PI / 180;
      const dLat = (latB - latA) * radians;
      const dLng = (lngB - lngA) * radians;
      const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(latA * radians) * Math.cos(latB * radians) * Math.sin(dLng / 2) ** 2;
      total += 12742000 * Math.asin(Math.min(1, Math.sqrt(a)));
    }
    return total;
  }
  const scoredSegments = active?.segments?.filter(segment => segment.cleanIndex !== null) ?? [];
  const scoredLength = scoredSegments.reduce((sum, segment) => sum + lengthM(segment.coordinates), 0);
  const meanCleanIndex = scoredLength > 0
    ? scoredSegments.reduce((sum, segment) =>
        sum + (segment.cleanIndex ?? 0) * lengthM(segment.coordinates), 0) / scoredLength
    : null;

  return (
    <section aria-label="모바일 경로 및 제보 패널"
      className={`absolute inset-x-0 bottom-0 z-[850] flex flex-col rounded-t-[26px] border border-slate-200 bg-white shadow-[0_-10px_36px_rgba(15,23,42,.16)] transition-[height] duration-200 ${expanded || pageMode === "report" ? "h-[min(68dvh,630px)]" : "h-[218px]"}`}
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
      <button type="button" aria-label={expanded ? "경로 패널 축소" : "경로 패널 펼치기"}
        aria-expanded={expanded} onClick={() => setExpanded(value => !value)}
        className="flex w-full shrink-0 justify-center pb-1 pt-2.5">
        <span className="h-1 w-8 rounded-full bg-slate-200" />
      </button>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pb-3">
        {expanded && pageMode === "safest" && (
          <div className="mb-3">
            <RoutePanel
              avoidanceLevel={avoidanceLevel}
              onAvoidanceLevelChange={onAvoidanceLevelChange}
            />
          </div>
        )}

        <div role="tablist" aria-label="모바일 경로 메뉴" className="mb-2 grid shrink-0 grid-cols-3 gap-1.5">
          {([
            ["shortest", "최단 경로"],
            ["safest", "회피 경로"],
            ["report", "흡연 제보"],
          ] as const).map(([mode, label]) => (
            <button type="button" role="tab" aria-selected={pageMode === mode} key={mode}
              onClick={() => { onTabChange(mode); if (mode === "report") setExpanded(true); }}
              className={`rounded-lg px-1 py-2 text-xs font-semibold ${pageMode === mode ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700"}`}>
              {label}
            </button>
          ))}
        </div>

        {pageMode === "report" ? (
          <div role="tabpanel" aria-label="흡연 제보 입력" className="min-h-0 space-y-2">
            {reportContent}
            {reportError && <p role="alert" className="text-xs text-red-700">{reportError}</p>}
          </div>
        ) : (
          <div role="tabpanel" aria-label="경로 요약" className="min-h-0">
            <div className="rounded-xl border border-teal-400 bg-teal-100/80 px-3 py-2.5">
              <p className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span>{pageMode === "shortest" ? "일반 최단 도보 경로" : "간접흡연 회피경로"}</span>
                <button type="button" onClick={() => setExpanded(value => !value)}
                  aria-label="경로 정보 자세히 보기" className="text-lg leading-none text-teal-500">›</button>
              </p>
              {active ? (
                <div className="mt-1 flex items-end justify-between gap-3">
                  <p className="shrink-0 text-[30px] font-bold leading-none tabular-nums text-slate-800">
                    {active.estimatedMinutes != null ? Math.round(active.estimatedMinutes) : "—"}<span className="ml-0.5 text-xs font-normal">분</span>
                  </p>
                  <p className="pb-0.5 text-right text-[11px] text-slate-500">
                    {(active.distanceM / 1000).toFixed(2)}km
                    {meanCleanIndex !== null && <> · 평균 청정지수 {meanCleanIndex.toFixed(0)}</>}
                  </p>
                </div>
              ) : <p className="mt-2 text-sm text-slate-600">출발지와 목적지를 입력해 경로를 검색하세요.</p>}
            </div>
            {loading && <p role="status" className="mt-1 text-[11px] text-slate-500">경로 계산 중… {elapsedSeconds.toFixed(1)}초</p>}
            {searchError && <p role="alert" className="mt-1 text-[11px] text-red-700">경로 탐색에 실패했습니다.</p>}
            <p className="mt-1.5 text-[10px] leading-4 text-slate-500">
              {pageMode === "shortest" ? "보행 거리만 고려한 최단 경로입니다." : "선택한 회피 강도와 숨길 AI 청정지수를 반영한 경로입니다."}
            </p>
            {expanded && (
              <div className="mt-4 space-y-3">
                <div>
                  <h3 className="text-[12px] font-bold text-slate-800">숨길 AI 모델 · 청정지수</h3>
                  <p className="mt-1 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-slate-700">
                    과거 담배꽁초 적발 기록과 주변 환경을 활용한 상대적 위험지수입니다.
                    실시간 흡연 여부나 대기질 측정값이 아닙니다.
                  </p>
                </div>
                {active && <CleanlinessLegend scope="route" embedded />}
                <p className="text-[10px] leading-4 text-slate-500">
                  청정지수가 높은 구간일수록 모델상 상대적으로 청정한 구간입니다.
                  모델 점수가 없는 구간은 안전하다고 판단하지 않습니다.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
