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
      aria-label="숨길AI 예측 청정지수 범례"
      className="absolute bottom-3 left-3 z-[500] w-[min(360px,calc(100%-24px))] rounded-xl bg-white/95 p-3 text-xs shadow-lg"
    >
      <p className="font-bold text-slate-800">숨길AI 예측 청정지수</p>
      <p className="mt-2 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-2 text-[11px] font-semibold leading-4 text-amber-950">
        과거 담배꽁초 적발 기록과 주변 환경을 활용한 상대적 예측지수입니다. 현재의 실제 흡연 여부나 대기질 측정값이 아닙니다.
      </p>
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
      </div>
      <p className="mt-2 text-[10px] leading-4 text-slate-500">
        청정지수가 높을수록 상대적으로 청정 · 미산정은 안전 판정이 아님
      </p>
    </div>
  );
}
