import type { TenantSession } from "./api/client";

const STORAGE_KEY = "velora_session";

export function loadSession(): TenantSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as TenantSession;
    return { ...parsed, email: parsed.email ?? "" };
  } catch {
    return null;
  }
}

export function saveSession(session: TenantSession) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
}

export function getChatSessionId(tenantId: string): string {
  const key = `velora_chat_${tenantId}`;
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export function resetChatSessionId(tenantId: string) {
  localStorage.removeItem(`velora_chat_${tenantId}`);
}
