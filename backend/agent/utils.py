"""
Utility helpers for the PocketFlow agent.

Includes LLM wrappers, embedding helpers, FAISS utilities, and chunking.
"""

from __future__ import annotations

import json
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
from duckduckgo_search import DDGS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """Call the OpenAI chat completion API and return plain text."""
    client = _get_openai_client()
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": "You are a meticulous research assistant that cites sources.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def get_embedding(text: str) -> List[float]:
    """Get an OpenAI embedding vector for the given text."""
    client = _get_openai_client()
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


def search_web_ddg(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Run a DuckDuckGo search; fall back to a placeholder on failure."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:
        return [
            {
                "title": "Search unavailable",
                "href": "",
                "body": f"Search failed: {exc}",
            }
        ]

    formatted = []
    for item in results:
        formatted.append(
            {
                "title": item.get("title", "Untitled"),
                "href": item.get("href", ""),
                "body": item.get("body", ""),
            }
        )
    return formatted


def fixed_size_chunk(text: str, chunk_size: int = 2000) -> List[str]:
    """Split text into fixed-size chunks."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


class RAGStore:
    """Wrapper around a FAISS index + metadata store."""

    def __init__(self, index_path: Path, store_path: Path) -> None:
        self.index_path = index_path
        self.store_path = store_path
        self.index: Optional[faiss.Index] = None
        self.items: List[Dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if not self.index_path.exists() or not self.store_path.exists():
            return
        self.index = faiss.read_index(str(self.index_path))
        with self.store_path.open("rb") as f:
            payload = pickle.load(f)
        self.items = payload.get("items", [])

    def search(self, embedding: List[float], top_k: int = 3) -> List[Dict[str, str]]:
        if not self.index or not self.items:
            return []
        vector = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vector)
        k = min(top_k, self.index.ntotal)
        if k == 0:
            return []
        distances, indices = self.index.search(vector, k)
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            item = self.items[idx]
            results.append(
                {
                    "text": item["text"],
                    "source": item["source"],
                    "score": float(score),
                }
            )
        return results


@lru_cache(maxsize=1)
def get_rag_store() -> RAGStore:
    """Return a cached FAISS store instance."""
    base_dir = Path(os.getenv("RAG_BASE_DIR", Path(__file__).resolve().parents[1]))
    index_path = Path(os.getenv("RAG_INDEX_PATH", base_dir / "data" / "index.faiss"))
    store_path = Path(os.getenv("RAG_STORE_PATH", base_dir / "data" / "store.pkl"))
    return RAGStore(index_path=index_path, store_path=store_path)

