import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  loading: boolean;
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

const LEVELS = ["low", "medium", "high"] as const;
const LABELS = ["낮음", "보통", "높음"] as const;
const DESCRIPTIONS = {
  low: "최단 거리와 비슷한 길을 우선하면서 상대적으로 위험점수가 낮은 길을 선택합니다.",
  medium: "조금 우회하더라도 모델 위험점수가 낮은 보행로를 선택할 수 있습니다.",
  high: "우회 거리가 늘어나더라도 모델 위험점수가 낮은 길을 더 적극적으로 탐색합니다.",
};

export default function RoutePanel({ avoidanceLevel, loading, onAvoidanceLevelChange }: Props) {
  const active = LEVELS.indexOf(avoidanceLevel);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label htmlFor="avoidance-level" className="text-sm font-bold text-slate-800">
          간접흡연 회피 강도
        </label>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
          {LABELS[active]}
        </span>
      </div>

      <input
        id="avoidance-level"
        type="range"
        min={0}
        max={2}
        step={1}
        value={active}
        onChange={event => onAvoidanceLevelChange(LEVELS[Number(event.target.value)])}
        aria-label="간접흡연 회피 강도"
        aria-valuetext={LABELS[active]}
        className="w-full cursor-pointer accent-green-600"
      />
      <div className="flex justify-between text-xs text-slate-600">
        {LABELS.map(label => <span key={label}>{label}</span>)}
      </div>

      <div className="rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-slate-700">
        {DESCRIPTIONS[avoidanceLevel]}
      </div>
      <p className="text-xs leading-5 text-slate-500">
        출발지와 목적지가 설정되어 있으면 강도를 바꿀 때 경로를 자동으로 다시 탐색합니다.
        {loading ? " 변경된 경로를 계산하는 중입니다." : " 실제 연기 노출이나 냄새의 체감 정도를 예측하는 설정은 아닙니다."}
      </p>
    </div>
  );
}
