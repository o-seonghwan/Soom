import type { Route } from "../types/route";

interface Props { route: Route | undefined; type: "shortest" | "safest"; }
export default function RouteResultPanel({ route, type }: Props) {
  const shortest = type === "shortest";
  const color = "#343A40";
  const foreground = "#FFFFFF";
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
        <span className="h-3 w-8 rounded-full" style={{ background: color }} />
        {shortest ? "최단 경로" : "간접흡연 회피 경로"}
      </div>
      {route ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl p-3" style={{ background: color, color: foreground }}>
              <p className="text-xs opacity-80">경로 거리</p>
              <p className="mt-2 text-lg font-bold">{route.distanceM.toLocaleString()}m</p>
            </div>
            <div className="rounded-xl p-3" style={{ background: color, color: foreground }}>
              <p className="text-xs opacity-80">예상 도보 시간</p>
              <p className="mt-2 text-lg font-bold">
                {route.estimatedMinutes == null ? "정보 없음" : `약 ${route.estimatedMinutes.toFixed(1)}분`}
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            {shortest ? "보행 거리만 고려한 경로입니다." : "선택한 회피 강도와 모델 위험점수를 반영한 경로입니다."}
          </p>
          {route.startSnapDistanceM != null && route.endSnapDistanceM != null && (
            <p className="text-xs leading-5 text-slate-500">
              보행로 접속 거리: 출발지 {route.startSnapDistanceM.toFixed(1)}m · 목적지 {route.endSnapDistanceM.toFixed(1)}m
            </p>
          )}
        </>
      ) : (
        <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">경로 탐색 후 거리와 도보 시간이 표시됩니다.</p>
      )}
    </div>
  );
}
