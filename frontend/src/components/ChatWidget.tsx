"use client";

import { FormEvent, useState } from "react";
import { sendChat, type ChatResponse } from "@/lib/api";

type Message = {
  author: "user" | "agent";
  text: string;
  sources?: string[];
};

export function ChatWidget() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!input.trim() || loading) {
      return;
    }
    const userText = input.trim();
    setMessages((prev) => [...prev, { author: "user", text: userText }]);
    setInput("");
    setError(null);
    setLoading(true);

    try {
      const response = await sendChat(userText);
      pushAgentMessage(response);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function pushAgentMessage(res: ChatResponse) {
    setMessages((prev) => [
      ...prev,
      { author: "agent", text: res.answer, sources: res.sources }
    ]);
  }

  return (
    <div className="panel">
      <h2>Chat</h2>
      <div className="messages">
        {messages.length === 0 && (
          <p className="placeholder">Start the conversation...</p>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`bubble ${msg.author}`}>
            <div>{msg.text}</div>
            {msg.sources && msg.sources.length > 0 && (
              <p className="sources">Sources: {msg.sources.join(", ")}</p>
            )}
          </div>
        ))}
        {loading && <p className="placeholder">Thinking...</p>}
      </div>
      {error && <p className="error">{error}</p>}
      <form className="input-row" onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about endurance training..."
        />
        <button type="submit" disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}

