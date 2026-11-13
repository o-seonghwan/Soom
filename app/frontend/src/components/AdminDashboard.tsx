
import { useState } from "react";

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
}


const reportTypeLabels: Record<Report["type"], string> = {
  smoking: "흡연 직접 목격",
  cigarette_butt: "담배꽁초 발견",
  other: "기타 흡연 관련 상황",
};


const statusLabels: Record<Report["status"], string> = {
  pending: "검토 대기",
  verified: "승인",
  rejected: "반려",
};


// =========================================
// 1. 관리자 인증 헤더
// =========================================

function makeAuthHeader(
  username: string,
  password: string
): string {
  return `Basic ${btoa(`${username}:${password}`)}`;
}


// =========================================
// 2. API 오류 메시지
// =========================================

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
    // JSON 형식이 아닌 오류는 기본 메시지 사용
  }

  return fallback;
}


// =========================================
// 3. 관리자 화면
// =========================================

export default function AdminDashboard({
  risks,
  onFocusLocation,
  onReviewCompleted,
}: AdminDashboardProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);

  const [adminReports, setAdminReports] =
    useState<AdminReport[]>([]);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [reviewNotes, setReviewNotes] =
    useState<Record<string, string>>({});

  const [updatingId, setUpdatingId] =
    useState<string | null>(null);


  // =======================================
  // 4. 관리자 제보 조회
  // =======================================

  async function fetchAdminReports(
    user: string,
    pass: string
  ): Promise<AdminReport[]> {
    const response = await fetch(
      `${API_BASE_URL}/api/admin/reports`,
      {
        headers: {
          Authorization: makeAuthHeader(user, pass),
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

    const data: unknown = await response.json();

    if (!Array.isArray(data)) {
      throw new Error(
        "관리자 제보 응답 형식이 올바르지 않습니다."
      );
    }

    return data as AdminReport[];
  }


  // =======================================
  // 5. 검토 의견 상태 초기화
  // =======================================

  function updateNotesFromReports(
    data: AdminReport[]
  ) {
    const notes: Record<string, string> = {};

    for (const report of data) {
      notes[report.id] = report.reviewNote ?? "";
    }

    setReviewNotes(notes);
  }


  // =======================================
  // 6. 관리자 로그인
  // =======================================

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

      setAuthorized(true);
      setMessage("관리자 로그인이 완료되었습니다.");
    } catch (err) {
      setAuthorized(false);
      setAdminReports([]);

      setError(
        err instanceof Error
          ? err.message
          : "관리자 로그인에 실패했습니다."
      );
    } finally {
      setBusy(false);
    }
  }


  // =======================================
  // 7. 로그아웃
  // =======================================

  function handleLogout() {
    setAuthorized(false);
    setUsername("");
    setPassword("");

    setAdminReports([]);
    setReviewNotes({});

    setError("");
    setMessage("로그아웃했습니다.");
  }


  // =======================================
  // 8. 관리자 제보 새로고침
  // =======================================

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


  // =======================================
  // 9. 관리자 승인·반려
  // =======================================

  async function handleReview(
    reportId: string,
    status: ReviewStatus
  ) {
    if (!authorized || updatingId || busy) {
      return;
    }

    const actionLabel =
      status === "verified" ? "승인" : "반려";

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

      // 관리자 화면 상태 업데이트
      setAdminReports((current) =>
        current.map((report) =>
          report.id === updated.id
            ? updated
            : report
        )
      );

      setReviewNotes((current) => ({
        ...current,
        [updated.id]: updated.reviewNote ?? "",
      }));

      setMessage(
        `제보가 ${actionLabel} 처리되었습니다.`
      );

      // 관리자 변경 사항을 공개 지도에 동기화
      // 공개 API를 다시 조회하므로 pending은 제외됨
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


  // =======================================
  // 10. 로그인 화면
  // =======================================

  if (!authorized) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            관리자 로그인
          </h2>

          <p className="mt-1 text-xs text-gray-500">
            관리자 계정으로 로그인해야
            제보 검토 기능을 사용할 수 있습니다.
          </p>
        </div>

        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
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

        <p className="text-xs text-gray-500">
          로컬 개발용 관리자 인증입니다.
          외부 배포 전 인증·세션·HTTPS 보완이 필요합니다.
        </p>
      </div>
    );
  }


  // =======================================
  // 11. 제보 통계
  // =======================================

  const total = adminReports.length;

  const pendingCount = adminReports.filter(
    (report) => report.status === "pending"
  ).length;

  const verifiedCount = adminReports.filter(
    (report) => report.status === "verified"
  ).length;

  const rejectedCount = adminReports.filter(
    (report) => report.status === "rejected"
  ).length;


  // =======================================
  // 12. 관리자 대시보드
  // =======================================

  return (
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
            onClick={() => void handleRefresh()}
            disabled={busy || updatingId !== null}
            className="rounded-lg bg-gray-100 px-3 py-2 text-sm disabled:opacity-50"
          >
            새로고침
          </button>

          <button
            type="button"
            onClick={handleLogout}
            disabled={busy || updatingId !== null}
            className="rounded-lg border px-3 py-2 text-sm disabled:opacity-50"
          >
            로그아웃
          </button>
        </div>
      </div>

      {/* 상태별 통계 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {[
          { label: "전체 제보", count: total },
          { label: "검토 대기", count: pendingCount },
          { label: "승인", count: verifiedCount },
          { label: "반려", count: rejectedCount },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-lg border bg-gray-50 p-3"
          >
            <p className="text-xs text-gray-500">
              {item.label}
            </p>

            <p className="mt-1 text-xl font-bold">
              {item.count}
            </p>
          </div>
        ))}
      </div>

      {/* 위험도 정보 */}
      <div className="rounded-lg border p-3">
        <p className="text-sm font-bold">
          위험도 데이터 현황
        </p>

        <p className="mt-1 text-sm text-gray-600">
          위치별 위험도: {risks.length}개
        </p>

        <p className="mt-1 text-xs text-gray-500">
          현재 위험도는 Mock 데이터이며,
          승인된 제보도 A*에 자동 반영되지 않습니다.
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

      {/* 전체 제보 목록 */}
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
              {report.description || "설명 없음"}
            </p>

            <button
              type="button"
              onClick={() =>
                onFocusLocation(report.location)
              }
              className="mt-2 rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700"
            >
              지도에서 위치 확인
            </button>

            <div className="mt-3 border-t pt-3">
              <label
                htmlFor={`review-${report.id}`}
                className="mb-1 block text-xs font-bold"
              >
                관리자 검토 의견
              </label>

              <textarea
                id={`review-${report.id}`}
                value={reviewNotes[report.id] ?? ""}
                maxLength={1000}
                rows={2}
                onChange={(event) =>
                  setReviewNotes((current) => ({
                    ...current,
                    [report.id]: event.target.value,
                  }))
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
                  disabled={updatingId !== null || busy}
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
                  disabled={updatingId !== null || busy}
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
        목록은 최신 500건까지 조회합니다.
        현재는 로컬 개발용 관리자 기능입니다.
      </p>
    </div>
  );
}
