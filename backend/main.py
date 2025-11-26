from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Deque, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.flow import create_research_flow

load_dotenv()

app = FastAPI(title="MainAgent Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_buffer: Deque[dict] = deque(maxlen=50)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question")
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    trace_id: str


class EvalResponse(BaseModel):
    recent: List[dict]


@app.get("/")
async def root():
    """API documentation and available endpoints."""
    return {
        "name": "MainAgent Backend API",
        "version": "0.1.0",
        "description": "Research agent with web search and RAG capabilities",
        "endpoints": {
            "GET /": "This page - API documentation",
            "GET /health": "Health check endpoint",
            "POST /api/chat": "Submit a question to the research agent",
            "GET /api/evals": "Get recent evaluation metrics",
            "GET /docs": "Interactive API documentation (Swagger UI)",
            "GET /redoc": "Alternative API documentation (ReDoc)"
        },
        "example_chat_request": {
            "message": "What is machine learning?",
            "session_id": "optional-session-id"
        }
    }


@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    flow = create_research_flow()
    shared = {
        "question": payload.message,
        "context": "",
        "search_history": [],
        "rag_results": [],
        "metrics": {"search_count": 0, "rag_hits": 0},
    }
    start = time.perf_counter()
    flow.run(shared)
    duration = time.perf_counter() - start

    entry = {
        "session_id": payload.session_id or "anonymous",
        "latency_ms": round(duration * 1000, 2),
        "searches": shared["metrics"]["search_count"],
        "rag_hits": shared["metrics"]["rag_hits"],
    }
    metrics_buffer.appendleft(entry)

    return ChatResponse(
        answer=shared.get("answer", ""),
        sources=[item["source"] for item in shared.get("rag_results", [])],
        trace_id=str(uuid.uuid4()),
    )


@app.get("/api/evals", response_model=EvalResponse)
async def evals_endpoint():
    return EvalResponse(recent=list(metrics_buffer))

