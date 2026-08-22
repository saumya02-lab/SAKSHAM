const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("saksham_token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ── Auth ──
export async function register(email: string, password: string, name: string) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  localStorage.setItem("saksham_token", data.access_token);
  return data;
}

export async function getMe() {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

export function logout() {
  localStorage.removeItem("saksham_token");
}

// ── Conversations ──
export async function getConversations() {
  const res = await fetch(`${API_BASE}/api/conversations`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function getConversation(id: string) {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export async function deleteConversation(id: string) {
  const res = await fetch(`${API_BASE}/api/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
}

// ── Chat (SSE) ──
export function streamChat(
  message: string,
  conversationId: string | null,
  agent: string,
  onEvent: (event: { type: string; data: any }) => void,
  onDone: (data: any) => void,
  onError: (error: Error) => void,
  regenerate: boolean = false,
): AbortController {
  const controller = new AbortController();
  const token = getToken();

  fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      agent,
      regenerate,
    }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Chat request failed");
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "message";

      const handleLine = (rawLine: string) => {
        const line = rawLine.replace(/\r$/, "");

        // Blank line terminates an SSE record.
        if (line === "") {
          currentEvent = "message";
          return;
        }
        // Comment / keep-alive ping.
        if (line.startsWith(":")) return;

        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
          return;
        }

        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) return;

          let data: any;
          try {
            data = JSON.parse(dataStr);
          } catch {
            return; // skip malformed JSON
          }

          if (currentEvent === "done") {
            onDone(data);
          } else {
            onEvent({ type: currentEvent, data });
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) handleLine(line);
      }

      // Flush anything left without a trailing newline.
      if (buffer) handleLine(buffer);
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err);
      }
    });

  return controller;
}

// ── Rate ──
export async function rateMessage(messageId: string, rating: string) {
  const res = await fetch(`${API_BASE}/api/messages/${messageId}/rate`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ rating }),
  });
  if (!res.ok) throw new Error("Failed to rate message");
}

// ── Documents ──
export async function getDocuments() {
  const res = await fetch(`${API_BASE}/api/documents`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocument(file: File) {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/documents`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteDocument(id: string) {
  const res = await fetch(`${API_BASE}/api/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete document");
}

// ── Agents ──
export async function getAgents() {
  const res = await fetch(`${API_BASE}/api/agents`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

// ── Memory ──
export async function getMemories() {
  const res = await fetch(`${API_BASE}/api/memory`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch memories");
  return res.json();
}

export async function deleteMemory(id: string) {
  const res = await fetch(`${API_BASE}/api/memory/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete memory");
}

export async function clearMemories() {
  const res = await fetch(`${API_BASE}/api/memory`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to clear memory");
  return res.json();
}

// ── Semantic document search ──
export interface SearchResult {
  chunk: string;
  score: number;
  source: string;
}

export async function searchDocuments(
  query: string,
  topK: number = 5
): Promise<SearchResult[]> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

// ── Settings ──
export async function getSettings() {
  const res = await fetch(`${API_BASE}/api/settings`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(data: Record<string, any>) {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

// ── Audit ──
export async function getAuditLogs() {
  const res = await fetch(`${API_BASE}/api/audit`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch audit logs");
  return res.json();
}
