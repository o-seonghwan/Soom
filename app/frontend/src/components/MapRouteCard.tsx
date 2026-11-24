import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import type { Coordinate } from "../types/route";
import { suggestAddresses, type AddressSuggestion } from "../services/addressSearchService";

type LocationMode = "start" | "end";

interface Props {
  start: Coordinate | null;
  end: Coordinate | null;
  startText: string;
  endText: string;
  selectionMode: LocationMode;
  loading: boolean;
  onMapSelect: (mode: LocationMode) => void;
  onTextChange: (mode: LocationMode, text: string) => void;
  onChoose: (mode: LocationMode, suggestion: AddressSuggestion) => void;
  onApplyText: (mode: LocationMode) => Promise<void>;
  onSwap: () => void;
  onSearch: () => void;
}

export default function MapRouteCard({
  start, end, startText, endText, selectionMode, loading,
  onMapSelect, onTextChange, onChoose, onApplyText, onSwap, onSearch,
}: Props) {
  const [activeMode, setActiveMode] = useState<LocationMode | null>(null);
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [searching, setSearching] = useState(false);
  const [lookupError, setLookupError] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [dropdownRect, setDropdownRect] = useState({ top: 0, left: 0, width: 0 });
  const requestSeq = useRef(0);
  const query = activeMode === "start" ? startText : activeMode === "end" ? endText : "";

  useEffect(() => {
    if (!activeMode || query.trim().length < 2) {
      setSuggestions([]);
      setSearching(false);
      setLookupError("");
      return;
    }
    const controller = new AbortController();
    const seq = ++requestSeq.current;
    setSearching(true);
    setLookupError("");
    const timer = window.setTimeout(() => {
      void suggestAddresses(query.trim(), controller.signal)
        .then(items => {
          if (seq !== requestSeq.current) return;
          setSuggestions(items);
          setActiveIndex(0);
        })
        .catch(err => {
          if (controller.signal.aborted || seq !== requestSeq.current) return;
          setSuggestions([]);
          setLookupError(err instanceof Error ? err.message : "주소 검색 실패");
        })
        .finally(() => {
          if (!controller.signal.aborted && seq === requestSeq.current) setSearching(false);
        });
    }, 300);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [activeMode, query]);

  // Render suggestions outside the map stacking context so the floating
  // results/report control can never cover them.
  useEffect(() => {
    if (!activeMode) return;
    function placeDropdown() {
      const rect = rootRef.current?.getBoundingClientRect();
      if (!rect) return;
      setDropdownRect({
        top: rect.bottom + 4,
        left: rect.left + 12,
        width: Math.max(180, rect.width - 24),
      });
    }
    placeDropdown();
    window.addEventListener("resize", placeDropdown);
    window.addEventListener("scroll", placeDropdown, true);
    return () => {
      window.removeEventListener("resize", placeDropdown);
      window.removeEventListener("scroll", placeDropdown, true);
    };
  }, [activeMode]);

  useEffect(() => {
    function handleOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node) &&
          !dropdownRef.current?.contains(event.target as Node)) setActiveMode(null);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  function selectSuggestion(mode: LocationMode, suggestion: AddressSuggestion) {
    onChoose(mode, suggestion);
    setActiveMode(null);
    setSuggestions([]);
    setLookupError("");
  }

  async function apply(mode: LocationMode) {
    setActiveMode(null);
    setSuggestions([]);
    await onApplyText(mode);
  }

  function onKeyDown(mode: LocationMode, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setActiveMode(null);
      return;
    }
    if (event.key === "ArrowDown" && suggestions.length) {
      event.preventDefault();
      setActiveIndex(current => (current + 1) % suggestions.length);
      return;
    }
    if (event.key === "ArrowUp" && suggestions.length) {
      event.preventDefault();
      setActiveIndex(current => (current + suggestions.length - 1) % suggestions.length);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      if (activeMode === mode && suggestions.length) selectSuggestion(mode, suggestions[activeIndex]);
      else void apply(mode);
    }
  }

  return (
    <div ref={rootRef} className="pointer-events-auto relative w-full max-w-[440px] rounded-3xl border border-white/90 bg-white/95 p-3 shadow-xl backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <div className="min-w-0 flex-1 space-y-2">
          {(["start", "end"] as const).map(mode => {
            const isStart = mode === "start";
            const value = isStart ? startText : endText;
            return (
              <div key={mode} className="flex items-center gap-1.5">
                <button type="button"
                  onClick={() => { setActiveMode(null); onMapSelect(mode); }}
                  aria-label={isStart ? "출발지를 지도에서 선택" : "목적지를 지도에서 선택"}
                  title={isStart ? "지도 클릭으로 출발지 선택" : "지도 클릭으로 목적지 선택"}
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition-colors ${isStart ? "bg-[#DCEBFF] text-[#2478FF]" : "bg-[#D2F8EC] text-[#0EB98B]"} ${selectionMode === mode ? (isStart ? "border-[#2478FF] ring-2 ring-[#2478FF]" : "border-[#0EB98B] ring-2 ring-[#0EB98B]") : (isStart ? "border-[#9AC9FF]" : "border-[#8CE8D2]")}`}>
                  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z"/>
                    <path d="M9 3v15M15 6v15"/>
                  </svg>
                </button>
                <input
                  aria-label={isStart ? "출발지 주소 입력" : "목적지 주소 입력"}
                  aria-expanded={activeMode === mode}
                  aria-autocomplete="list"
                  role="combobox"
                  autoComplete="off"
                  value={value}
                  placeholder={isStart ? "출발지 주소 또는 장소 검색" : "목적지 주소 또는 장소 검색"}
                  onFocus={() => { setActiveMode(mode); setActiveIndex(0); }}
                  onChange={event => { onTextChange(mode, event.target.value); setActiveMode(mode); }}
                  onKeyDown={event => onKeyDown(mode, event)}
                  className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm text-slate-800 focus:border-green-600 focus:outline-none"
                />
              </div>
            );
          })}
        </div>
        <div className="flex shrink-0 flex-col items-center gap-1">
          <button type="button" onClick={() => { setActiveMode(null); onSwap(); }}
            aria-label="출발지와 목적지 바꾸기" title="출발지와 목적지 바꾸기"
            className="rounded-full px-2 py-1 text-xl text-slate-600 hover:bg-slate-100">↕</button>
          <button type="button" onClick={onSearch} disabled={!start || !end || loading}
            aria-label={loading ? "경로 탐색 중" : "경로 탐색"}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-600 text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-40">
            {loading ? <span className="text-[10px] font-bold">탐색 중</span> : (
              <svg aria-hidden="true" width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="11" cy="11" r="7" /><path d="m20 20-4-4"/>
              </svg>
            )}
          </button>
        </div>
      </div>
      {activeMode && createPortal(
        <div ref={dropdownRef} role="listbox" aria-label={activeMode === "start" ? "출발지 연관 주소" : "목적지 연관 주소"}
          style={{ top: dropdownRect.top, left: dropdownRect.left, width: dropdownRect.width }}
          className="fixed z-[2000] max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 shadow-2xl">
          {query.trim().length < 2 ? (
            <p className="p-3 text-xs text-slate-600">도로명 주소나 장소명을 두 글자 이상 입력하세요.</p>
          ) : searching ? (
            <p className="p-3 text-xs text-slate-600">연관 주소 검색 중...</p>
          ) : lookupError ? (
            <p role="alert" className="p-3 text-xs text-red-700">{lookupError}</p>
          ) : suggestions.length ? (
            suggestions.map((item, index) => (
              <button key={`${item.id}-${item.lat}-${item.lng}`} type="button" role="option"
                aria-selected={index === activeIndex}
                onMouseDown={event => event.preventDefault()}
                onClick={() => selectSuggestion(activeMode, item)}
                className={`block w-full rounded-lg p-2 text-left text-sm hover:bg-green-50 ${index === activeIndex ? "bg-green-50" : ""}`}>
                <span className="block truncate font-semibold text-slate-900">{item.title || item.address}</span>
                <span className="block truncate text-xs text-slate-500">{item.kind} · {item.address}</span>
              </button>
            ))
          ) : (
            <p className="p-3 text-xs text-slate-600">
              검색 결과가 없습니다. 상세 주소를 입력하고 Enter를 눌러 적용하거나 지도 아이콘을 이용하세요.
            </p>
          )}
        </div>,
        document.body
      )}
    </div>
  );
}
