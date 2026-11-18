import { getCleanColor } from "../utils/cleanColor";

type LegendScope = "route" | "network";

interface CleanlinessLegendProps {
  scope: LegendScope;
}

/**
 * Shared cleanliness legend for B2C routes and the B2G walking network.
 * Gray always means no computed model score, not confirmed clean air.
 * A separate B2C swatch explains the inactive route.
 */
export default function CleanlinessLegend({ scope }: CleanlinessLegendProps) {
  const ranges = [
    { value: 10, label: "0–19" },
    { value: 30, label: "20–39" },
    { value: 50, label: "40–59" },
    { value: 70, label: "60–79" },
    { value: 90, label: "80–100" },
  ];

  return (
    <div
      aria-label="보행 링크 청정지수 범례"
      className="absolute bottom-3 left-3 z-[500] w-[min(360px,calc(100%-24px))] rounded-xl bg-white/95 p-3 text-xs shadow-lg"
    >
      <p className="font-bold text-slate-800">보행 링크 청정지수 · AI 모델</p>
      <p className="mt-1 text-[10px] text-slate-500">
        {scope === "route" ? "선택 경로의 링크별 예측지수" : "전체 보행로의 링크별 예측지수"}
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 text-[10px] text-slate-600">
        {ranges.map(({ value, label }) => (
          <span key={value} className="inline-flex items-center gap-1">
            <span className="h-2.5 w-4 rounded" style={{ background: getCleanColor(value) }} />
            {label}
          </span>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-600">
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-4 rounded bg-[#64748b]" />
          회색: 위험지수 미산정 구간
        </span>
        {scope === "route" && (
          <span className="inline-flex items-center gap-1">
            <span className="h-2.5 w-4 rounded bg-[#94a3b8]" />
            미선택 경로
          </span>
        )}
      </div>
      <p className="mt-2 text-[10px] leading-4 text-slate-500">
        청정지수가 높을수록 상대적으로 청정 · 미산정은 안전 판정이 아님 · 실측 대기질 아님
      </p>
    </div>
  );
}
