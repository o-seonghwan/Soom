
import { getRiskColor } from "../utils/riskColor";

const levels = [
  { score: 90, label: "매우 높음", range: "80~100" },
  { score: 70, label: "높음", range: "60~79" },
  { score: 50, label: "보통", range: "40~59" },
  { score: 30, label: "낮음", range: "20~39" },
  { score: 10, label: "매우 낮음", range: "0~19" },
];

export default function RiskLegend() {
  return (
    <div className="absolute bottom-4 left-3 z-[500] rounded-xl bg-white/95 p-3 shadow-lg">
      <h3 className="mb-2 text-sm font-bold">
        간접흡연 위험도
      </h3>

      <div className="space-y-2">
        {levels.map((level) => (
          <div
            key={level.score}
            className="flex items-center gap-2 text-xs"
          >
            <span
              className="h-3 w-3 rounded-full"
              style={{
                backgroundColor: getRiskColor(level.score),
              }}
            />

            <span className="w-16">{level.label}</span>
            <span className="text-gray-500">
              {level.range}
            </span>
          </div>
        ))}
      </div>

      <p className="mt-2 text-[10px] text-gray-500">
        ※ 현재 점수는 예시 데이터
      </p>
    </div>
  );
}
