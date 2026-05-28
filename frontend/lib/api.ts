export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function saveClaimToHistory(claim: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  const entry = { ...claim, analyzedAt: new Date().toISOString() };
  const existing = JSON.parse(localStorage.getItem("claimHistory") || "[]");
  const updated = [entry, ...existing].slice(0, 50);
  localStorage.setItem("claimHistory", JSON.stringify(updated));
}

export function getClaimHistory(): Record<string, unknown>[] {
  if (typeof window === "undefined") return [];
  return JSON.parse(localStorage.getItem("claimHistory") || "[]");
}
