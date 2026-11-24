import { useEffect, useId, useRef, useState } from "react";
import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

/** Shared B2C appearance, preserving update-on-release routing behavior. */
export default function RoutePanel({ avoidanceLevel, onAvoidanceLevelChange }: Props) {
  const id = useId();
  const [draft, setDraft] = useState(avoidanceLevel);
  const [previousLevel, setPreviousLevel] = useState(avoidanceLevel);
  const lastCommitted = useRef(avoidanceLevel);

  if (previousLevel !== avoidanceLevel) {
    setPreviousLevel(avoidanceLevel);
    setDraft(avoidanceLevel);
  }

  useEffect(() => {
    lastCommitted.current = avoidanceLevel;
  }, [avoidanceLevel]);

  function commit(value: number) {
    const next = Math.max(0, Math.min(100, Math.round(value / 20) * 20));
    if (next === lastCommitted.current) return;
    lastCommitted.current = next;
    onAvoidanceLevelChange(next);
  }

  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2.5">
      <div className="mb-1.5 flex justify-between text-xs font-bold text-slate-800">
        <label htmlFor={id}>회피 강도</label>
        <output htmlFor={id} className="text-emerald-700">{draft}%</output>
      </div>
      <div className="relative py-1">
        <input id={id} aria-label="간접흡연 회피 강도" type="range"
          min={0} max={100} step={20} value={draft}
          onChange={event => setDraft(Number(event.currentTarget.value))}
          onPointerUp={event => commit(Number(event.currentTarget.value))}
          onKeyUp={event => commit(Number(event.currentTarget.value))}
          onBlur={event => commit(Number(event.currentTarget.value))}
          className="relative z-10 block w-full cursor-pointer accent-emerald-500"
        />
      </div>
      <div aria-hidden="true" className="flex justify-between px-1.5">
        {[0, 20, 40, 60, 80, 100].map(level => (
          <span key={level} className="h-1.5 w-1.5 rounded-full bg-slate-400" />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>거리 우선</span><span>위험 회피 우선</span>
      </div>
    </div>
  );
}
