import { ChatWidget } from "@/components/ChatWidget";
import { EvalPanel } from "@/components/EvalPanel";
import "./globals.css";

export default function Home() {
  return (
    <main className="app-shell">
      <ChatWidget />
      <EvalPanel />
    </main>
  );
}

