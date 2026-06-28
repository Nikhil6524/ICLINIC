import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../../../hooks/useWebSocketChat";

interface ChatWindowProps {
  messages: ChatMessage[];
  isTyping: boolean;
  isConnected: boolean;
  onSendMessage: (content: string) => void;
}

const SUGGESTIONS = [
  "Book an appointment",
  "Check availability",
  "Cancel my appointment",
  "Reschedule a visit",
  "Talk to a human",
];

export function ChatWindow({ messages, isTyping, isConnected, onSendMessage }: ChatWindowProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || !isConnected) return;

    onSendMessage(trimmed);
    setInput("");

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize textarea
    const target = e.target;
    target.style.height = "auto";
    target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
  };

  const handleSuggestionClick = (suggestion: string) => {
    if (!isConnected) return;
    onSendMessage(suggestion);
  };

  return (
    <>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10H5a2 2 0 0 0-2 2v1a8 8 0 0 0 16 0v-1a2 2 0 0 0-2-2Z" />
                <path d="M12 18v4" />
              </svg>
            </div>
            <h3>How can I help you?</h3>
            <p>I can help you book appointments, check doctor availability, reschedule or cancel visits.</p>
            <div className="chat-empty-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chat-empty-suggestion"
                  onClick={() => handleSuggestionClick(s)}
                  disabled={!isConnected}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isTyping && (
          <div className="chat-bubble assistant">
            <div className="bubble-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <div className="chat-input-wrapper">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={!isConnected}
            rows={1}
            aria-label="Chat message input"
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || !isConnected}
            aria-label="Send message"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </div>
      </form>
    </>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const timeStr = message.timestamp.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (message.role === "system") {
    return (
      <div className="chat-system-message">
        <span>{message.content}</span>
      </div>
    );
  }

  return (
    <div className={`chat-bubble ${message.role}`}>
      <div className="bubble-content">
        <p>{message.content}</p>
      </div>
      <span className="bubble-time">{timeStr}</span>
    </div>
  );
}
