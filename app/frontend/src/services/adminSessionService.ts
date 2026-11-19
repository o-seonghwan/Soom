/** Cookie-only admin sessions. Never put passwords or bearer secrets in storage. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export interface AdminSession {
  authenticated: boolean;
  username: string;
  csrfToken: string;
  expiresAt: number;
}
export async function authError(response: Response, fallback: string): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") return data.detail;
  } catch { /* use fallback */ }
  return fallback;
}
export async function startAdminSession(username: string, password: string, remember: boolean): Promise<AdminSession> {
  const response = await fetch(`${API_BASE_URL}/api/admin/session`, {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, remember }),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await authError(response, "관리자 로그인에 실패했습니다."));
  return response.json() as Promise<AdminSession>;
}
export async function restoreAdminSession(): Promise<AdminSession | null> {
  const response = await fetch(`${API_BASE_URL}/api/admin/me`, {
    credentials: "include", cache: "no-store",
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(await authError(response, "관리자 로그인 상태를 확인할 수 없습니다."));
  return response.json() as Promise<AdminSession>;
}
export async function endAdminSession(csrfToken: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/admin/session`, {
    method: "DELETE", credentials: "include", cache: "no-store",
    headers: { "X-CSRF-Token": csrfToken },
  });
  if (!response.ok && response.status !== 401) throw new Error(await authError(response, "로그아웃 요청에 실패했습니다."));
}
