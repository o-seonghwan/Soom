
import { useState } from "react";

import type { Report } from "../types/report";
import type { RiskLocation } from "../types/risk";
import type { Coordinate } from "../types/route";

interface AdminDashboardProps {
  reports: Report[];
  risks: RiskLocation[];
  onFocusLocation: (point: Coordinate) => void;
}

type ReportFilter = "all" | Report["status"];

const typeLabels: Record<Report["type"], string> = {
  smoking: "흡연 직접 목격",
  cigarette_butt: "담배꽁초 발견",
  other: "기타",
};

const statusLabels: Record<Report["status"], string> = {
  pending: "검토 대기",
  verified: "확인",
  rejected: "반려",
};

export default function AdminDashboard({
  reports,
  risks,
  onFocusLocation,
}: AdminDashboardProps) {
  const [filter, setFilter] = useState<ReportFilter>("all");

  // 제보 통계
  const totalReports = reports.length;
  const pendingReports = reports.filter(
    (r) => r.status === "pending"
  ).length;

  // 위험지역 통계
  const totalRisks = risks.length;
  const highRisks = risks.filter(
    (r) => r.score >= 80
  ).length;

  // 제보 유형별 통계
  const typeStats = [
    {
      key: "smoking",
      label: "흡연 직접 목격",
      color: "#7c3aed",
    },
    {
      key: "cigarette_butt",
      label: "담배꽁초 발견",
      color: "#a78bfa",
    },
    {
      key: "other",
      label: "기타",
      color: "#c4b5fd",
    },
  ].map((item) => ({
    ...item,
    count: reports.filter((r) => r.type === item.key).length,
  }));

  // 상태 필터 적용 및 최신순 정렬
  const filteredReports = reports
    .filter((report) =>
      filter === "all" ? true : report.status === filter
    )
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() -
        new Date(a.createdAt).getTime()
    );

  const statCards = [
    { label: "전체 제보", value: totalReports, unit: "건" },
    { label: "검토 대기", value: pendingReports, unit: "건" },
    { label: "위험도 지점", value: totalRisks, unit: "곳" },
    { label: "고위험 지점", value: highRisks, unit: "곳" },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold">
          관리자 대시보드
        </h2>
        <p className="text-xs text-gray-500">
          프로토타입 · Mock 데이터 통계
        </p>
      </div>

      {/* 주요 통계 */}
      <div className="grid grid-cols-2 gap-2">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl bg-gray-100 p-4"
          >
            <p className="text-xs text-gray-500">
              {stat.label}
            </p>
            <p className="mt-1 text-2xl font-bold">
              {stat.value}
              <span className="ml-1 text-sm font-normal">
                {stat.unit}
              </span>
            </p>
          </div>
        ))}
      </div>

      {/* 제보 유형별 통계 */}
      <div className="rounded-xl border p-4">
        <h3 className="mb-3 font-bold">
          제보 유형별 현황
        </h3>

        <div className="space-y-3">
          {typeStats.map((item) => {
            const percentage =
              totalReports > 0
                ? (item.count / totalReports) * 100
                : 0;

            return (
              <div key={item.key}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{item.label}</span>
                  <span>{item.count}건</span>
                </div>

                <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: item.color,
                      width: `${percentage}%`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 제보 목록 */}
      <div className="rounded-xl border p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold">제보 목록</h3>

          <select
            aria-label="제보 상태 필터"
            value={filter}
            onChange={(e) =>
              setFilter(e.target.value as ReportFilter)
            }
            className="rounded-lg border p-2 text-sm"
          >
            <option value="all">전체</option>
            <option value="pending">검토 대기</option>
            <option value="verified">확인</option>
            <option value="rejected">반려</option>
          </select>
        </div>

        {filteredReports.length === 0 ? (
          <p className="py-5 text-center text-sm text-gray-500">
            표시할 제보가 없습니다.
          </p>
        ) : (
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {filteredReports.map((report) => (
              <div
                key={report.id}
                className="rounded-lg bg-gray-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-bold">
                    {typeLabels[report.type]}
                  </p>

                  <span className="rounded-full bg-purple-100 px-2 py-1 text-xs text-purple-700">
                    {statusLabels[report.status]}
                  </span>
                </div>

                <p className="mt-2 text-xs text-gray-500">
                  목격:{" "}
                  {new Date(
                    report.observedAt
                  ).toLocaleString("ko-KR")}
                </p>

                <p className="text-xs text-gray-500">
                  등록:{" "}
                  {new Date(
                    report.createdAt
                  ).toLocaleString("ko-KR")}
                </p>

                {report.description && (
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm">
                    {report.description}
                  </p>
                )}

                <button
                  onClick={() =>
                    onFocusLocation(report.location)
                  }
                  className="mt-3 rounded-lg bg-purple-100 px-3 py-2 text-xs font-medium text-purple-700"
                >
                  지도에서 위치 보기
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500">
        ※ 통계는 현재 화면에 불러온 데이터 기준입니다.
        관리자 인증, 제보 검증 및 영구 저장 기능은
        구현되지 않았습니다.
      </p>
    </div>
  );
}
