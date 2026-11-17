import type { Coordinate } from "../types/route";

interface Props {
  start: Coordinate | null;
  end: Coordinate | null;
  startAddress: string | null | undefined;
  endAddress: string | null | undefined;
  selectionMode: "start" | "end";
  loading: boolean;
  onSelect: (mode: "start" | "end") => void;
  onSwap: () => void;
  onSearch: () => void;
}

function label(point: Coordinate | null, address: string | null | undefined, fallback: string) {
  if (address) return address;
  if (point) return address === undefined ? "주소 확인 중…" : "주소 확인 불가";
  return fallback;
}

export default function MapRouteCard({
  start, end, startAddress, endAddress, selectionMode, loading, onSelect, onSwap, onSearch,
}: Props) {
  return (
    <div className="pointer-events-auto flex w-full max-w-[440px] items-center gap-2 rounded-3xl border border-white/90 bg-white/95 px-3 py-3 shadow-xl backdrop-blur-sm">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <div className="flex flex-col items-center gap-1">
          <span className="h-3 w-3 rounded-full border-[3px] border-blue-500 bg-white" />
          <span className="h-5 border-l-2 border-dotted border-slate-300" />
          <span className="h-3 w-3 rounded-full border-[3px] border-[#72EFDD] bg-white" />
        </div>
        <div className="min-w-0 flex-1">
          <button type="button" onClick={() => onSelect("start")}
            className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm ${selectionMode === "start" ? "bg-blue-50 text-blue-700" : "text-slate-700"}`}
            title={startAddress ?? "지도에서 출발지 선택"}>
            {label(start, startAddress, "출발지를 지도에서 선택")}
          </button>
          <div className="my-1 border-t border-slate-200" />
          <button type="button" onClick={() => onSelect("end")}
            className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-sm ${selectionMode === "end" ? "bg-teal-50 text-teal-800" : "text-slate-700"}`}
            title={endAddress ?? "지도에서 목적지 선택"}>
            {label(end, endAddress, "목적지를 지도에서 선택")}
          </button>
        </div>
        <button type="button" onClick={onSwap} aria-label="출발지와 목적지 바꾸기"
          className="shrink-0 rounded-full px-1.5 py-2 text-xl text-slate-600 hover:bg-slate-100" title="출발지와 목적지 바꾸기">↕</button>
      </div>
      <button type="button" onClick={onSearch} disabled={!start || !end || loading}
        className="shrink-0 rounded-2xl bg-[#343A40] px-3 py-3 text-xs font-bold text-white shadow-sm hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40">
        {loading ? "탐색 중" : "경로 탐색"}
      </button>
    </div>
  );
}
