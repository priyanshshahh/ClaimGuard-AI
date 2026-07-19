export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ApiError = Error & { status?: number; detail?: string };

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("cg_access_token");
  if (token) return { Authorization: `Bearer ${token}` };
  const apiKey = localStorage.getItem("cg_api_key");
  if (apiKey) return { "X-API-Key": apiKey };
  return {};
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit & { signal?: AbortSignal },
): Promise<T> {
  const headers: Record<string, string> = {
    ...getAuthHeader(),
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (init?.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(
      (typeof body.detail === "string" && body.detail) ||
        `API ${path} failed: ${res.status}`,
    ) as ApiError;
    err.status = res.status;
    err.detail = body.detail;
    throw err;
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function getClaimHistory(): Record<string, unknown>[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(localStorage.getItem("claimHistory") || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveClaimToHistory(claim: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  const entry = { ...claim, analyzedAt: new Date().toISOString() };
  const existing = getClaimHistory();
  const updated = [entry, ...existing].slice(0, 50);
  try {
    localStorage.setItem("claimHistory", JSON.stringify(updated));
  } catch {
    // Ignore quota / serialization failures — history is a best-effort convenience.
  }
}
