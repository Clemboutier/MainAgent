"use client";

import { useEffect, useState } from "react";
import { fetchEvalMetrics, type EvalSnapshot } from "@/lib/api";

export function EvalPanel() {
  const [metrics, setMetrics] = useState<EvalSnapshot[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const data = await fetchEvalMetrics();
        if (mounted) {
          setMetrics(data);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError((err as Error).message);
        }
      }
    }
    load();
    const id = setInterval(load, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="panel">
      <h2>Evaluation</h2>
      {error && <p className="error">{error}</p>}
      {metrics.length === 0 && !error && (
        <p className="placeholder">Interact to populate telemetry.</p>
      )}
      <ul className="stats">
        {metrics.map((entry, idx) => (
          <li key={idx}>
            <span>{entry.session_id}</span>
            <strong>{entry.latency_ms}ms · S:{entry.searches} · R:{entry.rag_hits}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

