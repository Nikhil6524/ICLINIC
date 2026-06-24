import { ChatWindow } from "./ChatWindow";
import { CallButton } from "./CallButton";
import { useWebSocketChat } from "../../../hooks/useWebSocketChat";
import "./Chat.css";

export function ChatPage() {
  const {
    messages,
    sendMessage,
    clearMessages,
    isConnected,
    isTyping,
    reconnect,
    sessionId,
  } = useWebSocketChat();

  return (
    <div className="chat-page">
      <div className="chat-container">
        <ChatHeader
          isConnected={isConnected}
          onClear={clearMessages}
          onReconnect={reconnect}
          sessionId={sessionId}
        />
        <ChatWindow
          messages={messages}
          isTyping={isTyping}
          onSendMessage={sendMessage}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
}

function ChatHeader({
  isConnected,
  onClear,
  onReconnect,
  sessionId,
}: {
  isConnected: boolean;
  onClear: () => void;
  onReconnect: () => void;
  sessionId: string | null;
}) {
  return (
    <div className="chat-header">
      <div className="chat-header-left">
        <div className="chat-avatar">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10H5a2 2 0 0 0-2 2v1a8 8 0 0 0 16 0v-1a2 2 0 0 0-2-2Z" />
            <path d="M12 18v4" />
          </svg>
        </div>
        <div className="chat-header-info">
          <h2>iClinic AI Assistant</h2>
          <span className={`chat-status ${isConnected ? "online" : "offline"}`}>
            <span className="status-dot"></span>
            {isConnected ? "Online" : "Reconnecting..."}
          </span>
        </div>
      </div>
      <div className="chat-header-actions">
        <CallButton sessionId={sessionId} />
        {!isConnected && (
          <button className="chat-action-btn" onClick={onReconnect} title="Reconnect">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 2v6h-6" />
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
              <path d="M3 22v-6h6" />
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
            </svg>
          </button>
        )}
        <button className="chat-action-btn" onClick={onClear} title="Clear chat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18" />
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
