const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface TenantSession {
  tenantId: string;
  apiKey: string;
  tenantName: string;
  email: string;
}

export interface AuthResponse {
  tenant_id: string;
  api_key: string;
  name: string;
  email: string;
}

export interface ConnectionInfo {
  db_name: string;
  db_type: string;
  description: string | null;
  status: string;
  onboarded_at: string | null;
}

export interface OnboardStatus {
  status: string;
  onboarded_at: string | null;
  message: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  apiKey?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return data as T;
}

export async function createTenant(name: string, email: string, password: string) {
  return request<AuthResponse>("/tenants", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function login(email: string, password: string) {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getConnection(tenantId: string, apiKey: string) {
  return request<ConnectionInfo>(`/connections/${tenantId}`, {}, apiKey);
}

export async function connectDatabase(
  tenantId: string,
  apiKey: string,
  body: {
    db_name: string;
    db_type: "postgres" | "mongodb";
    conn_string: string;
    description: string;
  }
) {
  return request(`/connections/${tenantId}`, {
    method: "POST",
    body: JSON.stringify(body),
  }, apiKey);
}

export async function disconnectDatabase(tenantId: string, apiKey: string) {
  return request(`/connections/${tenantId}`, { method: "DELETE" }, apiKey);
}

export async function startOnboarding(tenantId: string, apiKey: string) {
  return request<{ status: string; message: string }>(
    `/onboard/${tenantId}`,
    { method: "POST" },
    apiKey
  );
}

export async function getOnboardStatus(tenantId: string, apiKey: string) {
  return request<OnboardStatus>(`/onboard/${tenantId}/status`, {}, apiKey);
}

export async function sendChat(
  tenantId: string,
  apiKey: string,
  message: string,
  sessionId: string
) {
  return request<{ answer: string; session_id: string }>(
    `/chat/${tenantId}`,
    {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId }),
    },
    apiKey
  );
}

export type ChatStreamEvent =
  | { type: "started" }
  | { type: "step"; status: "start" | "end"; tool: string; message?: string }
  | { type: "done"; answer: string; session_id: string }
  | { type: "error"; message: string };

export async function streamChat(
  tenantId: string,
  apiKey: string,
  message: string,
  sessionId: string,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/${tenantId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("Streaming not supported by this browser");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part
        .split("\n")
        .find((entry) => entry.startsWith("data: "));
      if (!line) continue;

      const event = JSON.parse(line.slice(6)) as ChatStreamEvent;
      onEvent(event);
    }
  }
}

export function authToSession(data: AuthResponse): TenantSession {
  return {
    tenantId: data.tenant_id,
    apiKey: data.api_key,
    tenantName: data.name,
    email: data.email,
  };
}
