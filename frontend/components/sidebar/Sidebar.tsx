"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  getConversations,
  deleteConversation,
  getDocuments,
  uploadDocument,
  deleteDocument,
  searchDocuments,
  type SearchResult,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";
import {
  Bot,
  MessageSquare,
  Trash2,
  Settings,
  LogOut,
  FileText,
  Upload,
  X,
  FolderOpen,
  Plus,
  Search,
} from "lucide-react";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Document {
  id: string;
  filename: string;
  status: string;
  created_at: string;
}

interface SidebarProps {
  activeConversationId?: string | null;
  onSelectConversation?: (id: string) => void;
  onNewChat?: () => void;
}

export default function Sidebar({
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: SidebarProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [showDocs, setShowDocs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  const loadConversations = useCallback(async () => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    try {
      const data = await getDocuments();
      setDocuments(data);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  }, []);

  useEffect(() => {
    loadConversations();
    loadDocuments();

    const handler = () => loadConversations();
    window.addEventListener("refresh-conversations", handler);
    return () => window.removeEventListener("refresh-conversations", handler);
  }, [loadConversations, loadDocuments]);

  // Ingestion runs in the background, so poll until nothing is pending.
  useEffect(() => {
    const pending = documents.some(
      (d) => d.status !== "ready" && d.status !== "failed"
    );
    if (!pending) return;

    const timer = setInterval(loadDocuments, 3000);
    return () => clearInterval(timer);
  }, [documents, loadDocuments]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      await loadDocuments();
    } catch (err: any) {
      alert(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Delete doc failed:", err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      setSearchResults(await searchDocuments(query, 5));
    } catch (err) {
      console.error("Search failed:", err);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div className="w-72 bg-[var(--bg-secondary)] border-r border-[var(--border)] flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-4 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Bot className="w-6 h-6 text-brand-500" />
          <span className="font-bold text-lg">SAKSHAM</span>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-1">
          Your AI team, in one place
        </p>

        <button
          onClick={onNewChat}
          className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        <div className="flex items-center justify-between px-2 py-1 mb-1">
          <span className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
            Chats
          </span>
        </div>

        {conversations.length === 0 ? (
          <div className="px-2 py-4 text-center text-sm text-[var(--text-muted)]">
            No conversations yet
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelectConversation?.(conv.id)}
              className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition text-sm ${
                conv.id === activeConversationId
                  ? "bg-brand-100 dark:bg-brand-900/40"
                  : "hover:bg-[var(--bg-tertiary)]"
              }`}
            >
              <MessageSquare className="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="truncate">{conv.title}</p>
                <p className="text-xs text-[var(--text-muted)]">
                  {formatDate(conv.updated_at)}
                </p>
              </div>
              <button
                onClick={(e) => handleDelete(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 text-[var(--text-muted)] hover:text-red-500 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Documents Panel */}
      <div className="border-t border-[var(--border)]">
        <button
          onClick={() => setShowDocs(!showDocs)}
          className="w-full flex items-center gap-2 px-4 py-3 text-sm hover:bg-[var(--bg-tertiary)] transition"
        >
          <FolderOpen className="w-4 h-4 text-[var(--text-muted)]" />
          <span>Documents ({documents.length})</span>
        </button>

        {showDocs && (
          <div className="px-3 pb-3 space-y-2">
            <label className="flex items-center gap-2 px-3 py-2 border border-dashed border-[var(--border)] rounded-lg cursor-pointer hover:bg-[var(--bg-tertiary)] transition text-xs">
              <Upload className="w-4 h-4 text-brand-500" />
              <span>{uploading ? "Uploading..." : "Upload PDF/TXT/DOCX"}</span>
              <input
                type="file"
                accept=".pdf,.txt,.docx"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
            </label>

            {documents.length > 0 && (
              <>
                <form onSubmit={handleSearch} className="flex items-center gap-1">
                  <div className="relative flex-1">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[var(--text-muted)]" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search your documents"
                      className="w-full pl-7 pr-2 py-1.5 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                  {searchResults !== null && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearchQuery("");
                        setSearchResults(null);
                      }}
                      className="p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                      title="Clear search"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </form>

                {searching && (
                  <p className="text-[11px] text-[var(--text-muted)] px-1">
                    Searching...
                  </p>
                )}

                {searchResults !== null && !searching && (
                  <div className="space-y-1.5">
                    {searchResults.length === 0 ? (
                      <p className="text-[11px] text-[var(--text-muted)] px-1">
                        No matches found.
                      </p>
                    ) : (
                      searchResults.map((r, i) => (
                        <div
                          key={i}
                          className="px-2 py-1.5 text-[11px] rounded-lg bg-[var(--bg-tertiary)]"
                        >
                          <div className="flex items-center justify-between gap-2 mb-0.5">
                            <span className="font-medium truncate">
                              {r.source}
                            </span>
                            <span className="text-[10px] text-[var(--text-muted)] flex-shrink-0">
                              {r.score.toFixed(2)}
                            </span>
                          </div>
                          <p className="text-[var(--text-muted)] line-clamp-3">
                            {r.chunk.slice(0, 180)}
                            {r.chunk.length > 180 ? "..." : ""}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </>
            )}

            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg bg-[var(--bg-tertiary)]"
              >
                <FileText className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                <span className="flex-1 truncate">{doc.filename}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded ${
                    doc.status === "ready"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : doc.status === "failed"
                      ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                  }`}
                >
                  {doc.status}
                </span>
                <button
                  onClick={() => handleDeleteDoc(doc.id)}
                  className="text-[var(--text-muted)] hover:text-red-500"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User / Settings */}
      <div className="border-t border-[var(--border)] px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900 flex items-center justify-center text-brand-600 dark:text-brand-400 text-sm font-medium">
              {user?.name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-[var(--text-muted)] truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <div className="flex items-center">
            <button
              onClick={() => router.push("/settings")}
              className="p-2 text-[var(--text-muted)] hover:text-brand-500 transition"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 text-[var(--text-muted)] hover:text-red-500 transition"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
