"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  User,
  Bot,
  Search,
  Code2,
  Mail,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  RotateCcw,
} from "lucide-react";
import { useState } from "react";

interface Citation {
  source_title?: string;
  source_url?: string;
  snippet?: string;
}

interface MessageBubbleProps {
  role: string;
  content: string;
  agent?: string | null;
  citations?: Citation[];
  isStreaming?: boolean;
  rating?: string | null;
  onRate?: (rating: string) => void;
  onRegenerate?: () => void;
}

const agentIcons: Record<string, React.ReactNode> = {
  research: <Search className="w-4 h-4" />,
  coding: <Code2 className="w-4 h-4" />,
  email: <Mail className="w-4 h-4" />,
};

const agentNames: Record<string, string> = {
  research: "Research Agent",
  coding: "Coding Agent",
  email: "Email/Writing Agent",
  supervisor: "Supervisor",
  calculator: "Calculator",
};

export default function MessageBubble({
  role,
  content,
  agent,
  citations,
  isStreaming,
  rating,
  onRate,
  onRegenerate,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 px-4 py-4 ${isUser ? "bg-transparent" : "bg-[var(--bg-secondary)]"}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-brand-100 text-brand-600 dark:bg-brand-900 dark:text-brand-300"
            : "bg-emerald-100 text-emerald-600 dark:bg-emerald-900 dark:text-emerald-300"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">
            {isUser ? "You" : agent ? agentNames[agent] || "SAKSHAM" : "SAKSHAM"}
          </span>
          {agent && !isUser && agentIcons[agent] && (
            <span className="text-[var(--text-muted)]">{agentIcons[agent]}</span>
          )}
        </div>

        <div className={`prose max-w-none text-sm ${isStreaming ? "streaming-cursor" : ""}`}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code(props: any) {
                const { children, className, node, ...rest } = props;
                const match = /language-(\w+)/.exec(className || "");
                const inline = !match;
                return !inline ? (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{ borderRadius: "0.5rem", fontSize: "0.8rem" }}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                ) : (
                  <code
                    className="bg-[var(--bg-tertiary)] px-1.5 py-0.5 rounded text-sm"
                    {...rest}
                  >
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {citations && citations.length > 0 && (
          <div className="mt-3 pt-2 border-t border-[var(--border)]">
            <p className="text-xs font-medium text-[var(--text-muted)] mb-1">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {citations.map((cite, i) => (
                <a
                  key={i}
                  href={cite.source_url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs px-2 py-1 bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 rounded-md hover:bg-brand-100 dark:hover:bg-brand-900/50 transition"
                  title={cite.snippet}
                >
                  [{i + 1}] {cite.source_title || "Source"}
                </a>
              ))}
            </div>
          </div>
        )}

        {!isUser && !isStreaming && (
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={copyToClipboard}
              className="p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition"
              title="Copy"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            {onRate && (
              <>
                <button
                  onClick={() => onRate("up")}
                  className={`p-1 transition ${
                    rating === "up"
                      ? "text-green-500"
                      : "text-[var(--text-muted)] hover:text-green-500"
                  }`}
                  title="Good response"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onRate("down")}
                  className={`p-1 transition ${
                    rating === "down"
                      ? "text-red-500"
                      : "text-[var(--text-muted)] hover:text-red-500"
                  }`}
                  title="Bad response"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>
              </>
            )}
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="p-1 text-[var(--text-muted)] hover:text-brand-500 transition"
                title="Regenerate response"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
