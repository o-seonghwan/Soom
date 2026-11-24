import { useId } from "react";
import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

/** Shared B2C slider style for desktop and mobile. */
export default function RoutePanel({ avoidanceLevel, onAvoidanceLevelChange }: Props) {
  const id = useId();
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2.5">
      <div className="mb-1.5 flex justify-between text-xs font-bold text-slate-800">
        <label htmlFor={id}>회피 강도</label>
        <output htmlFor={id} className="text-emerald-700">{avoidanceLevel}%</output>
      </div>
      <input id={id} aria-label="간접흡연 회피 강도" type="range"
        min={0} max={100} step={20} value={avoidanceLevel}
        onChange={event => onAvoidanceLevelChange(Number(event.currentTarget.value))}
        className="w-full accent-emerald-500"
      />
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>거리 우선</span><span>위험 회피 우선</span>
      </div>
    </div>
  );
}
