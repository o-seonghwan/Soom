import type { Route } from "../types/route";

interface Props {
  route: Route | undefined;
  type: "shortest" | "safest";
}

/** Desktop result card mirrors the mobile B2C mint route summary. */
export default function RouteResultPanel({ route, type }: Props) {
  const shortest = type === "shortest";
  return (
    <div className="space-y-2">
      <div className="rounded-xl border border-teal-400 bg-teal-100/80 px-3 py-2.5">
        <p className="text-xs font-semibold text-slate-700">
          {shortest ? "일반 최단 도보 경로" : "간접흡연 회피경로"}
        </p>
        {route ? (
          <div className="mt-1 flex items-end justify-between gap-3">
            <p className="shrink-0 text-[30px] font-bold leading-none tabular-nums text-slate-800">
              {route.estimatedMinutes == null ? "—" : Math.round(route.estimatedMinutes)}
              <span className="ml-0.5 text-xs font-normal">분</span>
            </p>
            <p className="pb-0.5 text-right text-[11px] text-slate-500">
              {(route.distanceM / 1000).toFixed(2)}km
              <span className="ml-1">· {route.distanceM.toLocaleString()}m</span>
            </p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            출발지와 목적지를 입력해 경로를 검색하세요.
          </p>
        )}
      </div>
      <p className="text-[10px] leading-4 text-slate-500">
        {shortest
          ? "보행 거리만 고려한 최단 경로입니다."
          : "선택한 회피 강도와 숨길 AI 청정지수를 반영한 경로입니다."}
      </p>
    </div>
  );
}
