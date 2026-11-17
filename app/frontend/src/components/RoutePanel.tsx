import { useEffect, useRef, useState } from "react";
import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

/** Compact persistent control next to the cleanliness toggle. */
export default function RoutePanel({ avoidanceLevel, onAvoidanceLevelChange }: Props) {
  const [draft, setDraft] = useState(avoidanceLevel);
  const lastCommitted = useRef(avoidanceLevel);

  useEffect(() => {
    setDraft(avoidanceLevel);
    lastCommitted.current = avoidanceLevel;
  }, [avoidanceLevel]);

  function commit(value: number) {
    const next = Math.max(0, Math.min(100, value));
    if (next === lastCommitted.current) return;
    lastCommitted.current = next;
    onAvoidanceLevelChange(next);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-3 py-2 shadow-lg backdrop-blur-sm">
      <div className="mb-1 flex items-center justify-between gap-2">
        <label htmlFor="avoidance-level" className="whitespace-nowrap text-xs font-bold text-slate-800">
          회피 강도
        </label>
        <output htmlFor="avoidance-level" className="text-xs font-bold tabular-nums text-green-700">
          {draft}%
        </output>
      </div>
      <input id="avoidance-level" type="range" min={0} max={100} step={1} value={draft}
        onChange={event => setDraft(Number(event.currentTarget.value))}
        onPointerUp={event => commit(Number(event.currentTarget.value))}
        onKeyUp={event => commit(Number(event.currentTarget.value))}
        onBlur={event => commit(Number(event.currentTarget.value))}
        aria-label="간접흡연 회피 강도" aria-valuetext={`${draft}%`}
        title="드래그 후 놓으면 경로가 갱신됩니다."
        className="block w-full cursor-pointer accent-green-600"
      />
      <div className="mt-0.5 flex justify-between gap-1 text-[10px] text-slate-500">
        <span>거리 우선</span>
        <span>회피 우선</span>
      </div>
    </div>
  );
}
