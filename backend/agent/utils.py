"""
Utility helpers for the PocketFlow agent.

Includes LLM wrappers, embedding helpers, Pinecone utilities, and chunking.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from duckduckgo_search import DDGS
from openai import OpenAI
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

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
    """Wrapper around a Pinecone index for vector search."""

    def __init__(self, index_name: str) -> None:
        self.index_name = index_name
        self.pc: Optional[Pinecone] = None
        self.index = None
        self._connect()

    def _connect(self) -> None:
        """Initialize connection to Pinecone."""
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is not set in environment variables")
        
        self.pc = Pinecone(api_key=api_key)
        
        # Check if index exists, if not create it
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            # Get embedding dimension from environment or use default for text-embedding-3-small
            dimension = int(os.getenv("PINECONE_DIMENSION", "1536"))
            
            # Create serverless index
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=os.getenv("PINECONE_CLOUD", "aws"),
                    region=os.getenv("PINECONE_REGION", "us-east-1")
                )
            )
        
        self.index = self.pc.Index(self.index_name)

    def search(self, embedding: List[float], top_k: int = 3) -> List[Dict[str, str]]:
        """Search for similar vectors in Pinecone index."""
        if not self.index:
            return []
        
        try:
            # Query Pinecone
            query_response = self.index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            results = []
            for match in query_response.matches:
                results.append({
                    "text": match.metadata.get("text", ""),
                    "source": match.metadata.get("source", "unknown"),
                    "score": float(match.score),
                })
            
            return results
        except Exception as e:
            print(f"Error querying Pinecone: {e}")
            return []


@lru_cache(maxsize=1)
def get_rag_store() -> RAGStore:
    """Return a cached Pinecone store instance."""
    index_name = os.getenv("PINECONE_INDEX_NAME", "mainagent-rag")
    return RAGStore(index_name=index_name)

