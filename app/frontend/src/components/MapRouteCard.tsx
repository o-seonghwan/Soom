import type { Coordinate } from "../types/route";

interface Props {
  start: Coordinate | null;
  end: Coordinate | null;
  selectionMode: "start" | "end";
  onSelect: (mode: "start" | "end") => void;
  onSwap: () => void;
}

function positionLabel(position: Coordinate | null, fallback: string) {
  return position ? `${position[0].toFixed(5)}, ${position[1].toFixed(5)}` : fallback;
}

/** Compact map overlay modeled on an origin/destination navigation card. */
export default function MapRouteCard({ start, end, selectionMode, onSelect, onSwap }: Props) {
  return (
    <div className="pointer-events-auto w-full max-w-[350px] rounded-3xl border border-white/90 bg-white/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="flex flex-col items-center gap-1">
          <span className="h-3 w-3 rounded-full border-[3px] border-blue-500 bg-white shadow-sm" />
          <span className="h-5 border-l-2 border-dotted border-slate-300" />
          <span className="h-3 w-3 rounded-full border-[3px] border-[#A68A64] bg-white shadow-sm" />
        </div>
        <div className="min-w-0 flex-1">
          <button type="button" onClick={() => onSelect("start")}
            className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm ${selectionMode === "start" ? "bg-blue-50 text-blue-700" : "text-slate-700"}`}
            title="지도에서 출발지 선택">
            {positionLabel(start, "출발지 선택")}
          </button>
          <div className="my-1 border-t border-slate-200" />
          <button type="button" onClick={() => onSelect("end")}
            className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm ${selectionMode === "end" ? "bg-amber-50 text-amber-800" : "text-slate-700"}`}
            title="지도에서 목적지 선택">
            {positionLabel(end, "목적지 선택")}
          </button>
        </div>
        <button type="button" onClick={onSwap} aria-label="출발지와 목적지 바꾸기"
          className="shrink-0 rounded-full p-2 text-2xl text-slate-600 hover:bg-slate-100" title="출발지와 목적지 바꾸기">↕</button>
      </div>
    </div>
  );
}
