
import type {
  Coordinate,
  Route,
  RouteRequest,
} from "../types/route";

type LocationMode = "start" | "end";
type SearchStatus = "idle" | "success" | "error";

interface RoutePanelProps {
  start: Coordinate | null;
  end: Coordinate | null;
  startText: string;
  endText: string;

  selectionMode: LocationMode;
  avoidanceLevel: RouteRequest["avoidanceLevel"];

  routes: Route[];
  loading: boolean;
  elapsedSeconds: number;
  searchStatus: SearchStatus;

  onStartTextChange: (value: string) => void;
  onEndTextChange: (value: string) => void;
  onApplyCoordinate: (mode: LocationMode) => void;
  onSelectLocation: (mode: LocationMode) => void;
  onUseCurrentLocation: () => void;
  onAvoidanceLevelChange: (
    value: RouteRequest["avoidanceLevel"]
  ) => void;
  onSearch: () => void;
  onReset: () => void;
}

export default function RoutePanel({
  start,
  end,
  startText,
  endText,
  selectionMode,
  avoidanceLevel,
  routes,
  loading,
  elapsedSeconds,
  searchStatus,
  onStartTextChange,
  onEndTextChange,
  onApplyCoordinate,
  onSelectLocation,
  onUseCurrentLocation,
  onAvoidanceLevelChange,
  onSearch,
  onReset,
}: RoutePanelProps) {
  return (
    <div className="space-y-3">
      {/* 지도 선택 상태 */}
      <p className="text-sm text-gray-600">
        지도 선택 모드:{" "}
        <strong className="text-green-700">
          {selectionMode === "start"
            ? "출발지"
            : "목적지"}
        </strong>
      </p>

      {/* 출발지 */}
      <div className="space-y-1">
        <label
          htmlFor="start-coordinate"
          className="text-sm font-bold"
        >
          출발지
        </label>

        <div className="flex flex-wrap gap-2">
          <input
            id="start-coordinate"
            type="text"
            value={startText}
            disabled={loading}
            onChange={(event) =>
              onStartTextChange(event.target.value)
            }
            placeholder="위도, 경도"
            className="min-w-0 flex-1 rounded-lg border p-3 text-sm"
          />

          <button
            type="button"
            disabled={loading}
            onClick={() => onApplyCoordinate("start")}
            className="rounded-lg bg-gray-100 px-3 text-sm disabled:opacity-50"
          >
            적용
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={() => onSelectLocation("start")}
            className={`rounded-lg px-3 text-sm disabled:opacity-50 ${
              selectionMode === "start"
                ? "bg-green-600 text-white"
                : "bg-green-100 text-green-800"
            }`}
          >
            지도 선택
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={onUseCurrentLocation}
            className="rounded-lg border px-3 text-sm disabled:opacity-50"
          >
            현재 위치
          </button>
        </div>
      </div>

      {/* 목적지 */}
      <div className="space-y-1">
        <label
          htmlFor="end-coordinate"
          className="text-sm font-bold"
        >
          목적지
        </label>

        <div className="flex flex-wrap gap-2">
          <input
            id="end-coordinate"
            type="text"
            value={endText}
            disabled={loading}
            onChange={(event) =>
              onEndTextChange(event.target.value)
            }
            placeholder="위도, 경도"
            className="min-w-0 flex-1 rounded-lg border p-3 text-sm"
          />

          <button
            type="button"
            disabled={loading}
            onClick={() => onApplyCoordinate("end")}
            className="rounded-lg bg-gray-100 px-3 text-sm disabled:opacity-50"
          >
            적용
          </button>

          <button
            type="button"
            disabled={loading}
            onClick={() => onSelectLocation("end")}
            className={`rounded-lg px-3 text-sm disabled:opacity-50 ${
              selectionMode === "end"
                ? "bg-green-600 text-white"
                : "bg-green-100 text-green-800"
            }`}
          >
            지도 선택
          </button>
        </div>
      </div>

      {/* 간접흡연 회피 강도 */}
      <div className="space-y-1">
        <label
          htmlFor="avoidance-level"
          className="text-sm font-bold"
        >
          간접흡연 회피 강도
        </label>

        <select
          id="avoidance-level"
          value={avoidanceLevel}
          disabled={loading}
          onChange={(event) =>
            onAvoidanceLevelChange(
              event.target.value as
                RouteRequest["avoidanceLevel"]
            )
          }
          className="w-full rounded-lg border p-3 text-sm"
        >
          <option value="low">낮음</option>
          <option value="medium">보통</option>
          <option value="high">높음</option>
        </select>

        <div className="rounded-lg bg-emerald-50 p-3 text-xs leading-5 text-slate-700">
          {avoidanceLevel === "low" && (
            <p><strong>낮음 · 가까운 길 우선</strong> — 불필요한 우회를 줄이면서, 비슷한 거리라면 모델 위험점수가 낮은 길을 선택합니다.</p>
          )}
          {avoidanceLevel === "medium" && (
            <p><strong>보통 · 거리와 회피의 균형</strong> — 조금 더 걸어도 상대적으로 위험점수가 낮은 길을 선택할 수 있습니다.</p>
          )}
          {avoidanceLevel === "high" && (
            <p><strong>높음 · 회피 우선</strong> — 우회 거리가 늘어나더라도 상대적으로 위험점수가 낮은 길을 더 적극적으로 선택합니다.</p>
          )}
          <p className="mt-1 text-slate-500">이는 예상 경로 선택 성향입니다. 실제 담배 냄새·연기 노출 정도나 회피 효과를 보장하지 않습니다. 일반 최단경로는 거리만 고려합니다.</p>
        </div>
      </div>

      {/* 탐색 버튼 */}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!start || !end || loading}
          onClick={onSearch}
          className="flex-1 rounded-lg bg-green-600 p-3 font-bold text-white disabled:bg-gray-300"
        >
          {loading ? "탐색 중..." : "경로 탐색"}
        </button>

        <button
          type="button"
          disabled={loading}
          onClick={onReset}
          className="rounded-lg border px-5 py-3 disabled:opacity-50"
        >
          초기화
        </button>
      </div>

      {/* 경로 탐색 진행 상태 */}
      {loading && (
        <div
          role="status"
          className="rounded-lg border border-blue-200 bg-blue-50 p-3"
        >
          <p className="text-sm font-bold text-blue-700">
            경로 탐색 중...
          </p>
          <p className="mt-1 text-xl font-bold text-blue-800">
            {elapsedSeconds.toFixed(1)}초 경과
          </p>
          <p className="mt-1 text-xs text-blue-600">
            저장된 강남구 보행 네트워크를 사용합니다.
          </p>
        </div>
      )}

      {/* 탐색 성공 */}
      {!loading && searchStatus === "success" && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3">
          <p className="text-sm font-bold text-green-700">
            경로 탐색 완료
          </p>
          <p className="mt-1 text-lg font-bold text-green-800">
            {elapsedSeconds.toFixed(1)}초 소요
          </p>
        </div>
      )}

      {/* 탐색 실패 */}
      {!loading && searchStatus === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3"
        >
          <p className="text-sm font-bold text-red-700">
            경로 탐색 실패
          </p>
          <p className="mt-1 text-lg font-bold text-red-800">
            {elapsedSeconds.toFixed(1)}초 경과
          </p>
        </div>
      )}

      {/* 경로별 탐색 결과 */}
      {routes.length > 0 && (
        <div className="space-y-2">
          {routes.map((route) => {
            const isShortest = route.id === "shortest";

            return (
              <div
                key={route.id}
                className={`rounded-lg border p-4 ${
                  isShortest
                    ? "border-blue-100 bg-blue-50"
                    : "border-green-100 bg-green-50"
                }`}
              >
                <p
                  className={`font-bold ${
                    isShortest
                      ? "text-blue-800"
                      : "text-green-800"
                  }`}
                >
                  {route.name}
                </p>

                <div className="mt-2 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500">
                      경로 거리
                    </p>
                    <p className="text-lg font-bold">
                      {route.distanceM.toLocaleString()}m
                    </p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500">
                      예상 도보 시간
                    </p>
                    <p className="text-lg font-bold">
                      {route.estimatedMinutes !== undefined
                        ? `약 ${route.estimatedMinutes.toFixed(1)}분`
                        : "정보 없음"}
                    </p>
                  </div>
                </div>

                {route.startSnapDistanceM !== undefined &&
                  route.endSnapDistanceM !== undefined && (
                    <div className="mt-3 rounded-lg bg-white p-3 text-xs text-gray-600">
                      <p className="font-bold text-gray-700">
                        보행로 연결 정보
                      </p>

                      <p className="mt-1">
                        출발지 → 보행로:{" "}
                        {route.startSnapDistanceM.toFixed(1)}m
                      </p>

                      <p>
                        목적지 → 보행로:{" "}
                        {route.endSnapDistanceM.toFixed(1)}m
                      </p>

                      <p className="mt-2 text-gray-500">
                        연결 거리는 클릭 지점부터 보행 링크까지의
                        직선거리이며 경로 거리에 포함되지 않습니다.
                      </p>
                    </div>
                  )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
