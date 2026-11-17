import { useEffect, useRef, useState } from "react";
import type { RouteRequest } from "../types/route";

interface Props {
  avoidanceLevel: RouteRequest["avoidanceLevel"];
  loading: boolean;
  onAvoidanceLevelChange: (value: RouteRequest["avoidanceLevel"]) => void;
}

export default function RoutePanel({ avoidanceLevel, loading, onAvoidanceLevelChange }: Props) {
  // Change the visual slider immediately, but only commit once the user
  // releases the pointer or completes a keyboard action.
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
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label htmlFor="avoidance-level" className="text-sm font-bold text-slate-800">
          간접흡연 회피 강도
        </label>
        <output htmlFor="avoidance-level" className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
          {draft}%
        </output>
      </div>

      <input
        id="avoidance-level"
        type="range"
        min={0}
        max={100}
        step={1}
        value={draft}
        onChange={event => setDraft(Number(event.currentTarget.value))}
        onPointerUp={event => commit(Number(event.currentTarget.value))}
        onKeyUp={event => commit(Number(event.currentTarget.value))}
        onBlur={event => commit(Number(event.currentTarget.value))}
        aria-label="간접흡연 회피 강도"
        aria-valuetext={`${draft}%`}
        className="w-full cursor-pointer accent-green-600"
      />
      <div className="flex justify-between text-xs text-slate-600">
        <span>거리 우선 · 0%</span>
        <span>위험 회피 우선 · 100%</span>
      </div>

      <div className="rounded-xl bg-emerald-50 p-3 text-xs leading-5 text-slate-700">
        회피 강도 {draft}%: 높을수록 위험점수에 더 큰 가중치를 적용합니다.
      </div>
      <p className="text-xs leading-5 text-slate-500">
        슬라이더를 드래그하는 동안 강도만 변경됩니다. 마우스나 손가락을 놓으면 경로를 다시 계산합니다.
        {loading ? " 경로를 계산하는 중입니다." : " 실제 연기 노출이나 냄새를 실시간 측정하는 설정은 아닙니다."}
      </p>
    </div>
  );
}
