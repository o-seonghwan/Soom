import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  loading: boolean;
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

export default function RoutePanel({ avoidanceLevel, loading, onAvoidanceLevelChange }: Props) {
  return (
    <div className="space-y-3">
      <label htmlFor="avoidance-level" className="block text-sm font-bold text-slate-800">
        간접흡연 회피 강도
      </label>
      <select id="avoidance-level" value={avoidanceLevel} disabled={loading}
        onChange={event => onAvoidanceLevelChange(event.target.value as RouteRequest["avoidanceLevel"])}
        className="w-full rounded-xl border border-slate-200 bg-white p-3 text-sm">
        <option value="low">낮음 · 가까운 길 우선</option>
        <option value="medium">보통 · 거리와 회피의 균형</option>
        <option value="high">높음 · 위험 회피 우선</option>
      </select>
      <div className="rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-slate-700">
        {avoidanceLevel === "low" && "최단 거리와 비슷한 길을 우선하면서 상대적으로 위험점수가 낮은 길을 선택합니다."}
        {avoidanceLevel === "medium" && "조금 우회하더라도 모델 위험점수가 낮은 보행로를 선택할 수 있습니다."}
        {avoidanceLevel === "high" && "우회 거리가 늘어나더라도 모델 위험점수가 낮은 길을 더 적극적으로 탐색합니다."}
      </div>
      <p className="text-xs leading-5 text-slate-500">
        실제 연기 노출이나 냄새의 체감 정도를 예측하는 설정은 아닙니다.
        출발지·목적지를 선택하고 좌상단의 경로 탐색 버튼을 누르세요.
      </p>
    </div>
  );
}
