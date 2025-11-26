const apiBase =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export type ChatResponse = {
  answer: string;
  sources: string[];
  trace_id: string;
};

export async function sendChat(message: string): Promise<ChatResponse> {
  const res = await fetch(`${apiBase}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });

  if (!res.ok) {
    throw new Error(`Chat request failed (${res.status})`);
  }

  return res.json();
}

export type EvalSnapshot = {
  session_id: string;
  latency_ms: number;
  searches: number;
  rag_hits: number;
};

export async function fetchEvalMetrics(): Promise<EvalSnapshot[]> {
  const res = await fetch(`${apiBase}/api/evals`, {
    method: "GET",
    cache: "no-store"
  });
  if (!res.ok) {
    throw new Error("Failed to load evaluation data");
  }
  const payload = await res.json();
  return payload.recent ?? [];
}

