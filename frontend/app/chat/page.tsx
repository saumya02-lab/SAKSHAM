"use client";

import { useState, useCallback } from "react";
import ChatWindow from "@/components/chat/ChatWindow";
import ChatHeader from "@/components/chat/ChatHeader";
import Sidebar from "@/components/sidebar/Sidebar";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState("auto");

  const handleNewChat = useCallback(() => {
    setConversationId(null);
  }, []);

  const handleSelectConversation = useCallback((id: string) => {
    setConversationId(id);
  }, []);

  const handleConversationCreated = useCallback((id: string) => {
    setConversationId(id);
    // Tell the sidebar to reload its conversation list.
    window.dispatchEvent(new CustomEvent("refresh-conversations"));
  }, []);

  return (
    <>
      <Sidebar
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
      />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <ChatHeader
          selectedAgent={selectedAgent}
          onAgentChange={setSelectedAgent}
          onNewChat={handleNewChat}
        />
        <ChatWindow
          conversationId={conversationId}
          selectedAgent={selectedAgent}
          onConversationCreated={handleConversationCreated}
        />
      </main>
    </>
  );
}
