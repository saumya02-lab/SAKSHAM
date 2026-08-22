"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import MessageInput from "./MessageInput";
import { streamChat, rateMessage, getConversation } from "@/lib/api";
import { Bot, Sparkles, Code2, Search, Mail } from "lucide-react";

interface Message {
  id?: string;
  role: string;
  content: string;
  agent?: string | null;
  citations?: any[];
  isStreaming?: boolean;
  rating?: string | null;
}

interface ChatWindowProps {
  conversationId: string | null;
  selectedAgent: string;
  onConversationCreated: (id: string) => void;
}

const EXAMPLE_PROMPTS = [
  { icon: <Search className="w-5 h-5" />, text: "Summarize the latest trends in EV batteries with sources", agent: "research" },
  { icon: <Code2 className="w-5 h-5" />, text: "Write a Python function to detect palindromes with tests", agent: "coding" },
  { icon: <Mail className="w-5 h-5" />, text: "Draft a friendly follow-up email to a client who missed a meeting", agent: "email" },
  { icon: <Sparkles className="w-5 h-5" />, text: "Research remote-work productivity and draft a short update email", agent: "multi" },
];

export default function ChatWindow({
  conversationId,
  selectedAgent,
  onConversationCreated,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const [routingInfo, setRoutingInfo] = useState<{
    agents: string[];
    reasoning: string;
    models: Record<string, { model: string; temperature: number }>;
  } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const convIdRef = useRef<string | null>(conversationId);
  // Which conversation the messages on screen belong to.
  const loadedIdRef = useRef<string | null>(conversationId);

  useEffect(() => {
    convIdRef.current = conversationId;

    // Already showing this conversation (e.g. we just created it by
    // streaming) -- refetching would duplicate what's on screen.
    if (loadedIdRef.current === conversationId) return;

    let cancelled = false;

    if (!conversationId) {
      loadedIdRef.current = null;
      setMessages([]);
      setToolStatus(null);
      return;
    }

    (async () => {
      try {
        const conv = await getConversation(conversationId);
        if (cancelled) return;
        loadedIdRef.current = conversationId;
        setMessages(
          (conv.messages || []).map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            agent: m.agent,
            citations: m.citations || [],
            rating: m.rating,
          }))
        );
        setToolStatus(null);
      } catch (err) {
        console.error("Failed to load conversation:", err);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const runStream = useCallback(
    (message: string, regenerate: boolean) => {
      const assistantMsg: Message = {
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => {
        if (regenerate) {
          // Replace the previous answer instead of appending a new turn.
          const trimmed = [...prev];
          while (
            trimmed.length > 0 &&
            trimmed[trimmed.length - 1].role === "assistant"
          ) {
            trimmed.pop();
          }
          return [...trimmed, assistantMsg];
        }
        return [...prev, { role: "user", content: message }, assistantMsg];
      });
      setIsStreaming(true);
      setToolStatus(null);
      setRoutingInfo(null);

      const controller = streamChat(
        message,
        convIdRef.current,
        selectedAgent,
        (event) => {
          if (event.type === "token") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                last.content += event.data.text;
              }
              return updated;
            });
          } else if (event.type === "agent") {
            setActiveAgent(event.data.agent);
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                last.agent = event.data.agent;
              }
              return updated;
            });
          } else if (event.type === "routing") {
            setRoutingInfo(event.data);
          } else if (event.type === "tool") {
            setToolStatus(event.data.tool);
          } else if (event.type === "citation") {
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last.role === "assistant") {
                last.citations = [...(last.citations || []), event.data];
              }
              return updated;
            });
          }
        },
        (doneData) => {
          setIsStreaming(false);
          setToolStatus(null);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              last.isStreaming = false;
              last.id = doneData.message_id;
            }
            return updated;
          });

          if (doneData.conversation_id && !convIdRef.current) {
            convIdRef.current = doneData.conversation_id;
            // Mark as already displayed so the id change doesn't refetch.
            loadedIdRef.current = doneData.conversation_id;
            onConversationCreated(doneData.conversation_id);
          }
        },
        (error) => {
          setIsStreaming(false);
          setToolStatus(null);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              last.content = `Error: ${error.message}. Please try again.`;
              last.isStreaming = false;
            }
            return updated;
          });
        },
        regenerate
      );

      abortRef.current = controller;
    },
    [selectedAgent, onConversationCreated]
  );

  const handleSend = useCallback(
    (message: string) => runStream(message, false),
    [runStream]
  );

  /** Re-answer the most recent question (FR-18). */
  const handleRegenerate = useCallback(() => {
    if (isStreaming) return;
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) return;
    runStream(lastUser.content, true);
  }, [messages, isStreaming, runStream]);

  const handleStop = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last.role === "assistant") {
        last.isStreaming = false;
      }
      return updated;
    });
  };

  const handleRate = async (messageId: string, rating: string) => {
    try {
      await rateMessage(messageId, rating);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, rating } : m))
      );
    } catch (err) {
      console.error("Failed to rate:", err);
    }
  };

  const handleExampleClick = (prompt: string) => {
    handleSend(prompt);
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex-1 flex flex-col items-center justify-center px-4 overflow-y-auto">
          <Bot className="w-16 h-16 text-brand-400 mb-4" />
          <h2 className="text-2xl font-semibold mb-2">How can I help you today?</h2>
          <p className="text-[var(--text-secondary)] mb-8 text-center max-w-md">
            I&apos;m SAKSHAM — your multi-agent AI assistant. I can research, code, and write for you.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
            {EXAMPLE_PROMPTS.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleExampleClick(prompt.text)}
                className="flex items-start gap-3 p-4 text-left border border-[var(--border)] rounded-xl hover:bg-[var(--bg-secondary)] transition text-sm"
              >
                <span className="text-brand-500 mt-0.5">{prompt.icon}</span>
                <span className="text-[var(--text-secondary)]">{prompt.text}</span>
              </button>
            ))}
          </div>
        </div>
        <MessageInput onSend={handleSend} isStreaming={false} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-3xl mx-auto pb-4">
          {messages.map((msg, i) => {
            const isLast = i === messages.length - 1;
            return (
              <MessageBubble
                key={i}
                role={msg.role}
                content={msg.content}
                agent={msg.agent}
                citations={msg.citations}
                isStreaming={msg.isStreaming}
                rating={msg.rating}
                onRate={msg.id ? (r) => handleRate(msg.id!, r) : undefined}
                onRegenerate={
                  isLast && msg.role === "assistant" && !isStreaming
                    ? handleRegenerate
                    : undefined
                }
              />
            );
          })}

          {routingInfo && (
            <div className="px-4 py-2">
              <div className="max-w-3xl mx-auto">
                <div className="text-[11px] bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg px-3 py-2 space-y-1">
                  <div className="flex items-center gap-2 font-medium text-brand-700 dark:text-brand-300">
                    <Sparkles className="w-3 h-3" />
                    Agent routing
                  </div>
                  <p className="text-[var(--text-secondary)]">
                    <span className="font-medium">Selected:</span>{" "}
                    {routingInfo.agents.join(" → ")}
                    {routingInfo.reasoning && (
                      <span className="text-[var(--text-muted)]"> — {routingInfo.reasoning}</span>
                    )}
                  </p>
                  {Object.entries(routingInfo.models).map(([agent, info]) => (
                    <p key={agent} className="text-[var(--text-muted)]">
                      {agent}: <code className="text-[10px] bg-[var(--bg-tertiary)] px-1 py-0.5 rounded">{info.model}</code>
                      {" "}(temp {info.temperature})
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {toolStatus && (
            <div className="px-4 py-2">
              <div className="max-w-3xl mx-auto">
                <span className="inline-flex items-center gap-2 text-xs text-[var(--text-muted)] bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-full">
                  <span className="animate-spin w-3 h-3 border-2 border-brand-500 border-t-transparent rounded-full" />
                  {toolStatus}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <MessageInput
        onSend={handleSend}
        onStop={handleStop}
        isStreaming={isStreaming}
      />
    </div>
  );
}
