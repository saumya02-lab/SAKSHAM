"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  getSettings,
  updateSettings,
  getAuditLogs,
  getMemories,
  deleteMemory,
  clearMemories,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { useTheme, Theme } from "@/lib/theme-context";
import {
  ArrowLeft,
  Save,
  User,
  Sliders,
  ScrollText,
  Brain,
  Trash2,
} from "lucide-react";

interface AuditLog {
  id: string;
  action: string;
  metadata_json: Record<string, any>;
  created_at: string;
}

interface MemoryItem {
  id: string;
  type: string;
  content: string;
  created_at: string;
}

const MODEL_OPTIONS = [
  { value: "", label: "Server default" },
  { value: "gpt-4o-mini", label: "gpt-4o-mini" },
  { value: "gpt-4o", label: "gpt-4o" },
  { value: "gemini-1.5-flash", label: "gemini-1.5-flash" },
  { value: "llama3", label: "llama3 (Ollama)" },
];

const AGENT_OPTIONS = [
  { value: "auto", label: "Auto (let the supervisor choose)" },
  { value: "research", label: "Research Agent" },
  { value: "coding", label: "Coding Agent" },
  { value: "email", label: "Email/Writing Agent" },
];

export default function SettingsPage() {
  const { user, loading, refreshUser } = useAuth();
  const router = useRouter();

  const { theme, setTheme } = useTheme();

  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const [defaultAgent, setDefaultAgent] = useState("auto");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const data = await getSettings();
        setName(data.name || "");
        setModel(data.settings?.model || "");
        setDefaultAgent(data.settings?.default_agent || "auto");
        // Theme lives in localStorage (applied pre-paint); only adopt the
        // server value if this device has no local preference yet.
        const savedTheme = data.settings?.theme as Theme | undefined;
        if (savedTheme && !localStorage.getItem("nexus_theme")) {
          setTheme(savedTheme);
        }
      } catch (err) {
        console.error("Failed to load settings:", err);
      }
      try {
        setLogs(await getAuditLogs());
      } catch (err) {
        console.error("Failed to load audit logs:", err);
      }
      try {
        setMemories(await getMemories());
      } catch (err) {
        console.error("Failed to load memories:", err);
      }
    })();
    // setTheme is stable (useCallback) so it is safe to omit here.
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      await updateSettings({
        name,
        settings: { model, theme, default_agent: defaultAgent },
      });
      await refreshUser();
      setStatus("Saved");
    } catch (err: any) {
      setStatus(err.message || "Failed to save");
    } finally {
      setSaving(false);
      setTimeout(() => setStatus(null), 3000);
    }
  };

  const handleForget = async (id: string) => {
    try {
      await deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      console.error("Failed to delete memory:", err);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Forget everything SAKSHAM has learned about you?")) return;
    try {
      await clearMemories();
      setMemories([]);
    } catch (err) {
      console.error("Failed to clear memory:", err);
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-brand-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-8">
        <button
          onClick={() => router.push("/chat")}
          className="flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-brand-500 transition mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to chat
        </button>

        <h1 className="text-2xl font-semibold mb-8">Settings</h1>

        <form onSubmit={handleSave} className="space-y-8">
          {/* Profile */}
          <section className="border border-[var(--border)] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <User className="w-4 h-4 text-brand-500" />
              <h2 className="font-medium">Profile</h2>
            </div>

            <label className="block text-sm text-[var(--text-secondary)] mb-1">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            />

            <label className="block text-sm text-[var(--text-secondary)] mb-1 mt-4">
              Email
            </label>
            <input
              type="email"
              value={user.email}
              disabled
              className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-tertiary)] text-[var(--text-muted)] cursor-not-allowed"
            />
          </section>

          {/* Preferences */}
          <section className="border border-[var(--border)] rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sliders className="w-4 h-4 text-brand-500" />
              <h2 className="font-medium">Preferences</h2>
            </div>

            <label className="block text-sm text-[var(--text-secondary)] mb-1">
              Preferred model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            >
              {MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <label className="block text-sm text-[var(--text-secondary)] mb-1 mt-4">
              Default agent
            </label>
            <select
              value={defaultAgent}
              onChange={(e) => setDefaultAgent(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            >
              {AGENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <label className="block text-sm text-[var(--text-secondary)] mb-1 mt-4">
              Theme
            </label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as Theme)}
              className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)] focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Applies immediately. Save to sync it to your account.
            </p>
          </section>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? "Saving..." : "Save changes"}
            </button>
            {status && (
              <span className="text-sm text-[var(--text-secondary)]">{status}</span>
            )}
          </div>
        </form>

        {/* Long-term memory */}
        <section className="border border-[var(--border)] rounded-xl p-6 mt-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-brand-500" />
              <h2 className="font-medium">What SAKSHAM remembers</h2>
            </div>
            {memories.length > 0 && (
              <button
                onClick={handleClearAll}
                className="text-xs text-red-500 hover:text-red-600 transition"
              >
                Clear all
              </button>
            )}
          </div>

          {memories.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">
              Nothing yet. Tell SAKSHAM things like &quot;always reply in
              bullet points&quot; and they&apos;ll show up here.
            </p>
          ) : (
            <div className="space-y-2">
              {memories.map((mem) => (
                <div
                  key={mem.id}
                  className="flex items-start justify-between gap-3 text-sm py-2 border-b border-[var(--border)] last:border-0"
                >
                  <div className="min-w-0">
                    <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-muted)] mr-2">
                      {mem.type}
                    </span>
                    <span className="text-[var(--text-secondary)]">
                      {mem.content}
                    </span>
                  </div>
                  <button
                    onClick={() => handleForget(mem.id)}
                    className="flex-shrink-0 p-1 text-[var(--text-muted)] hover:text-red-500 transition"
                    title="Forget this"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Audit log */}
        <section className="border border-[var(--border)] rounded-xl p-6 mt-8">
          <div className="flex items-center gap-2 mb-4">
            <ScrollText className="w-4 h-4 text-brand-500" />
            <h2 className="font-medium">Recent activity</h2>
          </div>

          {logs.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">No activity yet.</p>
          ) : (
            <div className="space-y-2">
              {logs.slice(0, 20).map((log) => (
                <div
                  key={log.id}
                  className="flex items-center justify-between text-sm py-1.5 border-b border-[var(--border)] last:border-0"
                >
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--bg-tertiary)]">
                    {log.action}
                  </span>
                  <span className="text-xs text-[var(--text-muted)]">
                    {formatDate(log.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
