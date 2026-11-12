
import { useState } from "react";

import type { Coordinate } from "../types/route";
import type {
  ReportRequest,
  ReportType,
} from "../types/report";

interface ReportFormProps {
  location: Coordinate | null;
  submitting: boolean;
  onSubmit: (report: ReportRequest) => Promise<boolean>;
  onSelectLocation: () => void;
  onCancel: () => void;
}

// 현재 시간을 datetime-local 입력 형식으로 변환
function getLocalDateTime(): string {
  const now = new Date();
  const local = new Date(
    now.getTime() - now.getTimezoneOffset() * 60000
  );

  return local.toISOString().slice(0, 16);
}

export default function ReportForm({
  location,
  submitting,
  onSubmit,
  onSelectLocation,
  onCancel,
}: ReportFormProps) {
  const [type, setType] = useState<ReportType>("smoking");
  const [observedAt, setObservedAt] =
    useState(getLocalDateTime);
  const [description, setDescription] = useState("");

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (!location) {
      alert("먼저 지도에서 제보 위치를 선택하세요.");
      return;
    }

    const date = new Date(observedAt);

    if (
      Number.isNaN(date.getTime()) ||
      date.getTime() > Date.now()
    ) {
      alert("유효한 목격 시간을 입력하세요.");
      return;
    }

    const success = await onSubmit({
      location,
      type,
      observedAt: date.toISOString(),
      description: description.trim(),
    });

    if (success) {
      setType("smoking");
      setDescription("");
      setObservedAt(getLocalDateTime());
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-xl border border-gray-200 bg-gray-50 p-4"
    >
      <h2 className="font-bold text-gray-800">
        흡연 관련 위치 제보
      </h2>

      <p className="text-xs text-gray-500">
        개인을 식별할 수 있는 정보는 작성하지 마세요.
      </p>

      {/* 제보 위치 */}
      <div>
        <label className="mb-1 block text-sm font-medium">
          제보 위치
        </label>

        <div className="flex flex-wrap items-center gap-2">
          <span className="min-w-0 flex-1 text-xs text-gray-600">
            {location
              ? `${location[0].toFixed(6)}, ${location[1].toFixed(6)}`
              : "선택된 위치 없음"}
          </span>

          <button
            type="button"
            onClick={onSelectLocation}
            className="rounded-lg bg-purple-100 px-3 py-2 text-sm text-purple-700"
          >
            지도에서 선택
          </button>
        </div>
      </div>

      {/* 제보 유형 */}
      <div>
        <label
          htmlFor="report-type"
          className="mb-1 block text-sm font-medium"
        >
          제보 유형
        </label>

        <select
          id="report-type"
          value={type}
          onChange={(e) =>
            setType(e.target.value as ReportType)
          }
          className="w-full rounded-lg border bg-white p-3 text-sm"
        >
          <option value="smoking">흡연 직접 목격</option>
          <option value="cigarette_butt">담배꽁초 발견</option>
          <option value="other">기타 흡연 관련 상황</option>
        </select>
      </div>

      {/* 목격 시간 */}
      <div>
        <label
          htmlFor="observed-at"
          className="mb-1 block text-sm font-medium"
        >
          목격 시간
        </label>

        <input
          id="observed-at"
          type="datetime-local"
          value={observedAt}
          max={getLocalDateTime()}
          onChange={(e) => setObservedAt(e.target.value)}
          required
          className="w-full rounded-lg border bg-white p-3 text-sm"
        />
      </div>

      {/* 설명 */}
      <div>
        <label
          htmlFor="report-description"
          className="mb-1 block text-sm font-medium"
        >
          추가 설명 (선택)
        </label>

        <textarea
          id="report-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={300}
          rows={3}
          placeholder="예: 건물 출입구 근처에서 흡연 목격"
          className="w-full rounded-lg border bg-white p-3 text-sm"
        />

        <p className="mt-1 text-right text-xs text-gray-400">
          {description.length}/300
        </p>
      </div>

      {/* 버튼 */}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!location || submitting}
          className="flex-1 rounded-lg bg-purple-600 p-3 font-bold text-white disabled:bg-gray-300"
        >
          {submitting ? "등록 중..." : "제보 등록"}
        </button>

        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border px-4"
        >
          취소
        </button>
      </div>

      <p className="text-xs text-gray-500">
        ※ 프로토타입 제보는 임시 저장되며 실제 신고로
        접수되지 않습니다.
      </p>
    </form>
  );
}
