import { useState, type FormEvent } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type Application = {
  id: string;
  username: string;
  email: string;
  organization: string;
  reason: string;
  status: string;
  requestedAt: string;
  reviewedAt: string | null;
  reviewedBy: string | null;
  reviewNote: string | null;
};

async function apiError(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
      return data.detail;
    }
  } catch { /* Response body is optional. */ }
  return `HTTP ${response.status}: 계정 요청을 처리할 수 없습니다.`;
}

export function AdminAccountApplication() {
  const [form, setForm] = useState({
    username: "", password: "", email: "", organization: "", reason: "",
  });
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(`${API_BASE}/api/admin/applications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) throw new Error(await apiError(response));
      setNotice("신청이 접수되었습니다. 제작자가 승인한 뒤 기존 로그인 창에서 로그인할 수 있습니다.");
      setForm({ username: "", password: "", email: "", organization: "", reason: "" });
    } catch (error) {
      setError(error instanceof Error ? error.message : "계정 신청에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={event => void submit(event)}
      className="space-y-3 rounded-xl border border-teal-200 bg-teal-50/50 p-3"
      aria-label="관리자 계정 신청">
      <h3 className="text-sm font-bold text-slate-800">관리자 계정 신청</h3>
      <p className="text-xs leading-5 text-slate-600">
        신청만으로 관리자 권한이 부여되지 않습니다. 제작자가 확인 후 승인해야 로그인할 수 있습니다.
      </p>
      {([
        ["username", "신청 아이디", "text", "영문으로 시작하는 4~40자"],
        ["password", "신청 비밀번호", "password", "12자 이상"],
        ["email", "이메일", "email", "답변받을 이메일"],
        ["organization", "소속 기관", "text", "학교·기관명"],
      ] as const).map(([field, label, type, placeholder]) => (
        <label key={field} className="block text-xs font-semibold text-slate-700">
          {label}
          <input
            type={type} required placeholder={placeholder}
            autoComplete={field === "password" ? "new-password" : "off"}
            minLength={field === "password" ? 12 : field === "username" ? 4 : undefined}
            value={form[field]}
            onChange={event => setForm(current => ({ ...current, [field]: event.target.value }))}
            className="mt-1 block w-full rounded-lg border border-slate-200 bg-white p-2.5 text-sm"
          />
        </label>
      ))}
      <label className="block text-xs font-semibold text-slate-700">
        신청 사유
        <textarea value={form.reason} required minLength={10} maxLength={800} rows={3}
          placeholder="관리자 권한이 필요한 이유를 10자 이상 입력해 주세요."
          onChange={event => setForm(current => ({ ...current, reason: event.target.value }))}
          className="mt-1 block w-full rounded-lg border border-slate-200 bg-white p-2.5 text-sm"/>
      </label>
      <button type="submit" disabled={loading}
        className="w-full rounded-lg bg-teal-700 p-2.5 text-sm font-bold text-white disabled:opacity-50">
        {loading ? "신청 중..." : "제작자에게 승인 요청"}
      </button>
      {notice && <p role="status" className="text-xs text-emerald-700">{notice}</p>}
      {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
    </form>
  );
}

export function OwnerApplications({ authorization }: { authorization: string }) {
  const [applications, setApplications] = useState<Application[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/admin/applications`, {
        headers: { Authorization: authorization },
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await apiError(response));
      setApplications(await response.json() as Application[]);
    } catch (error) {
      setError(error instanceof Error ? error.message : "신청 목록을 확인할 수 없습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function review(application: Application, decision: "approved" | "rejected" | "disabled") {
    if (!window.confirm(`${application.username} 계정을 ${decision === "approved" ? "승인" : decision === "disabled" ? "비활성화" : "반려"}할까요?`)) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/admin/applications/${application.id}`, {
        method: "PATCH",
        headers: { Authorization: authorization, "Content-Type": "application/json" },
        body: JSON.stringify({ decision, reviewNote: "" }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      setMessage(`${application.username} 계정을 처리했습니다.`);
      // Refresh inline to avoid reusing event handler after mutation.
      const listResponse = await fetch(`${API_BASE}/api/admin/applications`, {
        headers: { Authorization: authorization }, cache: "no-store",
      });
      if (!listResponse.ok) throw new Error(await apiError(listResponse));
      setApplications(await listResponse.json() as Application[]);
    } catch (error) {
      setError(error instanceof Error ? error.message : "승인 처리에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="제작자 전용 관리자 계정 승인" className="space-y-3 rounded-xl border border-teal-300 p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-800">관리자 계정 승인 · 제작자 전용</h3>
          <p className="mt-1 text-[11px] text-slate-500">승인 전 계정은 관리자 API에 접근할 수 없습니다.</p>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={busy}
          className="shrink-0 rounded-lg bg-teal-100 px-3 py-2 text-xs font-semibold text-teal-800 disabled:opacity-50">
          신청 목록 조회
        </button>
      </div>
      {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
      {message && <p role="status" className="text-xs text-emerald-700">{message}</p>}
      {applications.length === 0 && <p className="text-xs text-slate-500">신청 목록을 조회해 주세요. 목록이 비어 있다면 신청 내역이 없는 것입니다.</p>}
      {applications.map(application => (
        <article key={application.id} className="space-y-2 rounded-lg border border-slate-200 bg-white p-3 text-xs">
          <p className="font-bold text-slate-800">{application.username} <span className="font-normal text-slate-500">({application.status})</span></p>
          <p className="break-all text-slate-600">{application.organization} · {application.email}</p>
          <p className="whitespace-pre-wrap text-slate-700">{application.reason}</p>
          <p className="text-[11px] text-slate-400">신청일: {new Date(application.requestedAt).toLocaleString("ko-KR")}</p>
          {application.status === "pending" && (
            <div className="flex gap-2">
              <button type="button" disabled={busy} onClick={() => void review(application, "approved")}
                className="flex-1 rounded-lg bg-emerald-600 p-2 text-white disabled:opacity-50">승인</button>
              <button type="button" disabled={busy} onClick={() => void review(application, "rejected")}
                className="flex-1 rounded-lg bg-slate-600 p-2 text-white disabled:opacity-50">반려</button>
            </div>
          )}
          {application.status === "approved" && (
            <button type="button" disabled={busy} onClick={() => void review(application, "disabled")}
              className="rounded-lg border border-red-300 px-3 py-2 text-red-700 disabled:opacity-50">계정 비활성화</button>
          )}
        </article>
      ))}
    </section>
  );
}
