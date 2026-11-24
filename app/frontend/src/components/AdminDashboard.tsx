
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AdminAccountApplication, OwnerApplications } from "./AdminAccountWorkflow";

import type { Coordinate } from "../types/route";
import type { RiskLocation } from "../types/risk";
import type { Report } from "../types/report";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";

type AdminReport = Report & {
  reviewedAt?: string | null;
  reviewNote?: string | null;
};

type ReviewStatus = "verified" | "rejected";

interface AdminDashboardProps {
  reports: Report[];
  risks: RiskLocation[];
  onFocusLocation: (point: Coordinate) => void;
  onReviewCompleted: () => Promise<void>;

  // B2G 지도에 관리자 신고 목록 전달
  onAdminReportsChange?: (
    reports: Report[] | null
  ) => void;
  onAuthorizedChange?: (authorized: boolean) => void;
  onSessionChange?: (authorizationHeader: string | null) => void;
  dashboardTarget?: HTMLElement | null;
  riskSource?: "model-csv" | null;
  logoutSignal?: number;
}

const reportTypeLabels: Record<
  Report["type"],
  string
> = {
  smoking: "흡연 직접 목격",
  cigarette_butt: "담배꽁초 발견",
  other: "기타 흡연 관련 상황",
};

const statusLabels: Record<
  Report["status"],
  string
> = {
  pending: "검토 대기",
  verified: "승인",
  rejected: "반려",
};

// 관리자 인증 헤더
function makeAuthHeader(
  username: string,
  password: string
): string {
  return `Basic ${btoa(`${username}:${password}`)}`;
}

// API 오류 메시지
async function getErrorMessage(
  response: Response,
  fallback: string
): Promise<string> {
  try {
    const data: unknown = await response.json();

    if (
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof data.detail === "string"
    ) {
      return data.detail;
    }
  } catch {
    // JSON 형식이 아니라면 기본 메시지 사용
  }

  return fallback;
}

export default function AdminDashboard({
  risks,
  onFocusLocation,
  onReviewCompleted,
  onAdminReportsChange,
  onAuthorizedChange,
  onSessionChange,
  dashboardTarget = null,
  riskSource = null,
  logoutSignal = 0,
}: AdminDashboardProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showApplication, setShowApplication] = useState(false);
  const [adminRole, setAdminRole] = useState<"owner" | "admin">("admin");

  const [authorized, setAuthorized] =
    useState(false);

  const [busy, setBusy] =
    useState(false);

  const [adminReports, setAdminReports] =
    useState<AdminReport[]>([]);

  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");

  const [reviewNotes, setReviewNotes] =
    useState<Record<string, string>>({});

  const [updatingId, setUpdatingId] =
    useState<string | null>(null);

  // 전체 관리자 신고 조회
  async function fetchAdminReports(
    user: string,
    pass: string
  ): Promise<AdminReport[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/reports`,
      {
        headers: {
          Authorization: makeAuthHeader(
            user,
            pass
          ),
        },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      throw new Error(
        await getErrorMessage(
          response,
          "관리자 제보 조회에 실패했습니다."
        )
      );
    }

    const data: unknown =
      await response.json();

    if (!Array.isArray(data)) {
      throw new Error(
        "관리자 제보 응답 형식이 올바르지 않습니다."
      );
    }

    return data as AdminReport[];
  }

  // 검토 의견 초기화
  function updateNotesFromReports(
    data: AdminReport[]
  ) {
    const notes: Record<string, string> = {};

    for (const report of data) {
      notes[report.id] =
        report.reviewNote ?? "";
    }

    setReviewNotes(notes);
  }

  // 관리자 로그인
  async function handleLogin() {
    if (!username.trim() || !password) {
      setError(
        "관리자 아이디와 비밀번호를 입력하세요."
      );
      return;
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const data = await fetchAdminReports(
        username,
        password
      );

      setAdminReports(data);
      updateNotesFromReports(data);

      // The server decides whether the account is the owner; a client-only
      // role flag never grants permission to approve applications.
      const profileResponse = await fetch(`${API_BASE_URL}/api/admin/me`, {
        headers: { Authorization: makeAuthHeader(username, password) },
        cache: "no-store",
      });
      if (!profileResponse.ok) throw new Error(await getErrorMessage(profileResponse, "관리자 권한을 확인할 수 없습니다."));
      const profile: { role?: string } = await profileResponse.json();
      setAdminRole(profile.role === "owner" ? "owner" : "admin");

      setAuthorized(true);
      onAuthorizedChange?.(true);
      onSessionChange?.(makeAuthHeader(username, password));
      setMessage("");

      // B2G 지도에 전체 신고 전달
      onAdminReportsChange?.(data);
    } catch (err) {
      setAuthorized(false);
      onAuthorizedChange?.(false);
      onSessionChange?.(null);
      setAdminReports([]);
      onAdminReportsChange?.(null);

      setError(
        err instanceof Error
          ? err.message
          : "관리자 로그인에 실패했습니다."
      );
    } finally {
      setBusy(false);
    }
  }

  // 관리자 로그아웃
  function handleLogout() {
    onAuthorizedChange?.(false);
    onSessionChange?.(null);
    setAuthorized(false);
    setAdminRole("admin");
    setUsername("");
    setPassword("");

    setAdminReports([]);
    setReviewNotes({});

    // B2G 지도도 공개 신고 상태로 복원
    onAdminReportsChange?.(null);

    setError("");
    setMessage("로그아웃했습니다.");
  }

  // Logout may also be initiated from the B2G header.
  // Only react to a nonzero explicit signal, not the initial mount.
  const lastLogoutSignal = useRef(logoutSignal);
  useEffect(() => {
    if (logoutSignal > 0 && logoutSignal !== lastLogoutSignal.current) handleLogout();
    lastLogoutSignal.current = logoutSignal;
  }, [logoutSignal]); // eslint-disable-line react-hooks/exhaustive-deps

  // 관리자 신고 새로고침
  async function handleRefresh() {
    if (!authorized) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const data = await fetchAdminReports(
        username,
        password
      );

      setAdminReports(data);
      updateNotesFromReports(data);

      // 지도 데이터 동기화
      onAdminReportsChange?.(data);

      setMessage(
        "최신 제보 목록을 불러왔습니다."
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "제보 목록 갱신에 실패했습니다."
      );
    } finally {
      setBusy(false);
    }
  }

  // 관리자 신고 승인·반려
  async function handleReview(
    reportId: string,
    status: ReviewStatus
  ) {
    if (!authorized || updatingId || busy) {
      return;
    }

    const actionLabel =
      status === "verified"
        ? "승인"
        : "반려";

    if (
      !window.confirm(
        `선택한 제보를 ${actionLabel}하시겠습니까?`
      )
    ) {
      return;
    }

    setUpdatingId(reportId);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/admin/reports/${reportId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: makeAuthHeader(
              username,
              password
            ),
          },
          body: JSON.stringify({
            status,
            reviewNote:
              reviewNotes[reportId] ?? "",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(
            response,
            "제보 검토 결과 저장에 실패했습니다."
          )
        );
      }

      const updated: AdminReport =
        await response.json();

      const nextReports =
        adminReports.map((report) =>
          report.id === updated.id
            ? updated
            : report
        );

      setAdminReports(nextReports);

      setReviewNotes((current) => ({
        ...current,
        [updated.id]:
          updated.reviewNote ?? "",
      }));

      // 수정된 신고를 B2G 지도에 반영
      onAdminReportsChange?.(nextReports);

      setMessage(
        `제보가 ${actionLabel} 처리되었습니다.`
      );

      // 공개 신고 목록도 갱신
      await onReviewCompleted();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "제보 검토에 실패했습니다."
      );
    } finally {
      setUpdatingId(null);
    }
  }

  // 로그인 화면
  if (!authorized) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            관리자 로그인
          </h2>

          <p className="mt-1 text-xs text-gray-500">
            관리자 계정으로 로그인해야
            전체 제보를 조회하고 검토할 수 있습니다.
          </p>
        </div>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            if (busy) return;
            void handleLogin();
          }}
        >
          <div>
            <label
              htmlFor="admin-username"
              className="mb-1 block text-sm font-bold"
            >
              관리자 아이디
            </label>

            <input
              id="admin-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
              className="w-full rounded-lg border p-3 text-sm"
              placeholder="관리자 아이디"
            />
          </div>

          <div>
            <label
              htmlFor="admin-password"
              className="mb-1 block text-sm font-bold"
            >
              비밀번호
            </label>

            <input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              className="w-full rounded-lg border p-3 text-sm"
              placeholder="비밀번호"
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-slate-700 p-3 font-bold text-white disabled:opacity-50"
          >
            {busy
              ? "로그인 확인 중..."
              : "로그인"}
          </button>
        </form>

        {error && (
          <p
            role="alert"
            className="text-sm text-red-600"
          >
            {error}
          </p>
        )}

        {message && (
          <p className="text-sm text-green-700">
            {message}
          </p>
        )}

        <div className="border-t border-slate-200 pt-3">
          <button type="button" onClick={() => setShowApplication(value => !value)}
            aria-expanded={showApplication}
            className="w-full rounded-lg border border-teal-200 bg-teal-50 px-3 py-2.5 text-sm font-bold text-teal-800">
            {showApplication ? "관리자 계정 신청 닫기" : "새 관리자 계정 신청"}
          </button>
          {showApplication && <div className="mt-3"><AdminAccountApplication /></div>}
        </div>
        <p className="text-xs text-gray-500">
          제작자 승인 후에만 관리자 데이터에 접근할 수 있습니다.
          접속 상태가 공유된 기기에서는 사용을 마친 뒤 사이트를 종료하세요.
        </p>
      </div>
    );
  }

  // 관리자 신고 현황
  const total = adminReports.length;

  const pendingCount =
    adminReports.filter(
      (report) =>
        report.status === "pending"
    ).length;

  const verifiedCount =
    adminReports.filter(
      (report) =>
        report.status === "verified"
    ).length;

  const rejectedCount =
    adminReports.filter(
      (report) =>
        report.status === "rejected"
    ).length;

  const dashboard = (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            관리자 대시보드
          </h2>

          <p className="text-xs text-gray-500">
            로그인 계정: {username}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              void handleRefresh();
            }}
            disabled={
              busy ||
              updatingId !== null
            }
            className="rounded-lg bg-gray-100 px-3 py-2 text-sm disabled:opacity-50"
          >
            새로고침
          </button>


        </div>
      </div>

      {adminRole === "owner" && (
        <OwnerApplications authorization={makeAuthHeader(username, password)} />
      )}

      {/* Match the actual B2G report marker fill/stroke colors in MapView. */}
      <section aria-label="지도 제보 마커 범례" className="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <h3 className="text-sm font-bold text-slate-800">지도 아이콘 안내 · 제보 상태</h3>
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-700">
          {[
            { label: "검토 대기", fill: "#fbbf24", stroke: "#b45309" },
            { label: "승인", fill: "#22c55e", stroke: "#15803d" },
            { label: "반려", fill: "#94a3b8", stroke: "#475569" },
          ].map(item => (
            <span key={item.label} className="inline-flex items-center gap-2">
              <span aria-hidden="true" className="inline-block h-3.5 w-3.5 shrink-0 rounded-full border-2"
                style={{ backgroundColor: item.fill, borderColor: item.stroke }} />
              {item.label}
            </span>
          ))}
        </div>
        <p className="mt-2 text-[11px] leading-4 text-slate-500">
          지도 원형 마커의 색상은 제보 처리 상태를 뜻합니다. 제보 종류와 상세 내용은 마커를 선택해 확인하세요.
          지도에서 제보 표시를 끄면 마커도 숨겨집니다.
        </p>
      </section>

      {/* 상태별 신고 통계 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          {
            label: "전체 제보",
            count: total,
          },
          {
            label: "검토 대기",
            count: pendingCount,
          },
          {
            label: "승인",
            count: verifiedCount,
          },
          {
            label: "반려",
            count: rejectedCount,
          },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-lg border bg-gray-50 p-3"
          >
            <p className="whitespace-nowrap text-xs text-gray-500">
              {item.label}
            </p>

            <p className="mt-1 text-xl font-bold">
              {item.count}
            </p>
          </div>
        ))}
      </div>

      {/* 위험도 데이터 현황 */}
      <div className="rounded-lg border p-3">
        <p className="text-sm font-bold">
          위험도 데이터 현황
        </p>

        <p className="mt-1 text-sm text-gray-600">
          위치별 위험도: {risks.length}개
        </p>

        <p className="mt-1 text-xs text-gray-500">
          {riskSource === "model-csv" ? "AI 모델 CSV 기반 위험도입니다." : "AI 모델 데이터가 연결되지 않았습니다."}
          승인된 제보는 A* 경로 계산에 자동 반영되지 않습니다.
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
        >
          {error}
        </p>
      )}

      {message && (
        <p
          role="status"
          className="rounded-lg bg-green-50 p-3 text-sm text-green-700"
        >
          {message}
        </p>
      )}

      {/* 전체 신고 목록 */}
      <div className="space-y-3">
        <h3 className="font-bold">
          제보 목록 ({total}건)
        </h3>

        {total === 0 && (
          <p className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
            등록된 제보가 없습니다.
          </p>
        )}

        {adminReports.map((report) => (
          <div
            key={report.id}
            className="rounded-lg border p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong className="text-sm">
                {reportTypeLabels[report.type]}
              </strong>

              <span className="rounded bg-gray-100 px-2 py-1 text-xs font-bold">
                {statusLabels[report.status]}
              </span>
            </div>

            <p className="mt-2 text-xs text-gray-500">
              목격 시각:{" "}
              {new Date(
                report.observedAt
              ).toLocaleString("ko-KR")}
            </p>

            <p className="mt-1 text-xs text-gray-500">
              등록 시각:{" "}
              {new Date(
                report.createdAt
              ).toLocaleString("ko-KR")}
            </p>

            <p className="mt-2 whitespace-pre-wrap text-sm">
              {report.description ||
                "설명 없음"}
            </p>

            <button
              type="button"
              onClick={() =>
                onFocusLocation(
                  report.location
                )
              }
              className="mt-2 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700"
            >
              지도에서 위치 확인
            </button>

            {/* 관리자 검토 */}
            <div className="mt-3 border-t pt-3">
              <label
                htmlFor={`review-${report.id}`}
                className="mb-1 block text-xs font-bold"
              >
                관리자 검토 의견
              </label>

              <textarea
                id={`review-${report.id}`}
                value={
                  reviewNotes[report.id] ?? ""
                }
                maxLength={1000}
                rows={2}
                onChange={(event) =>
                  setReviewNotes(
                    (current) => ({
                      ...current,
                      [report.id]:
                        event.target.value,
                    })
                  )
                }
                className="w-full rounded-lg border p-2 text-sm"
                placeholder="검토 의견 (선택사항)"
              />

              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() =>
                    void handleReview(
                      report.id,
                      "verified"
                    )
                  }
                  disabled={
                    updatingId !== null ||
                    busy
                  }
                  className="flex-1 rounded-lg bg-green-600 p-2 text-sm font-bold text-white disabled:opacity-50"
                >
                  {updatingId === report.id
                    ? "처리 중..."
                    : "승인"}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    void handleReview(
                      report.id,
                      "rejected"
                    )
                  }
                  disabled={
                    updatingId !== null ||
                    busy
                  }
                  className="flex-1 rounded-lg bg-red-600 p-2 text-sm font-bold text-white disabled:opacity-50"
                >
                  반려
                </button>
              </div>

              {report.reviewedAt && (
                <p className="mt-2 text-xs text-gray-500">
                  최종 검토 시각:{" "}
                  {new Date(
                    report.reviewedAt
                  ).toLocaleString("ko-KR")}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-500">
        신고 목록은 최신 500건까지 조회합니다.
        현재는 로컬 개발용 관리자 기능입니다.
      </p>
    </div>
  );
  // Keep auth state and review actions mounted, but show their dashboard
  // exclusively inside the authenticated local-government analysis tab.
  return dashboardTarget ? createPortal(dashboard, dashboardTarget) : null;
}
