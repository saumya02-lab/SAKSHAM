"use client";

import { useState, useEffect } from "react";
import { getAgents } from "@/lib/api";
import { Plus, Bot } from "lucide-react";
import ThemeToggle from "@/components/ThemeToggle";

interface Agent {
  key: string;
  name: string;
  description: string;
}

interface ChatHeaderProps {
  selectedAgent: string;
  onAgentChange: (agent: string) => void;
  onNewChat: () => void;
}

export default function ChatHeader({
  selectedAgent,
  onAgentChange,
  onNewChat,
}: ChatHeaderProps) {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    getAgents().then(setAgents).catch(console.error);
  }, []);

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="flex items-center gap-3">
        <Bot className="w-6 h-6 text-brand-500" />
        <h1 className="text-lg font-semibold">SAKSHAM</h1>
      </div>

      <div className="flex items-center gap-4">
        <ThemeToggle />

        <div className="flex items-center gap-2">
          <label className="text-sm text-[var(--text-secondary)]">Agent:</label>
          <select
            value={selectedAgent}
            onChange={(e) => onAgentChange(e.target.value)}
            className="text-sm px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            {agents.map((agent) => (
              <option key={agent.key} value={agent.key}>
                {agent.name}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>
    </div>
  );
}
