"""Node definitions for the research agent."""

from __future__ import annotations
import json
from typing import Any, Dict, List
from pocketflow import Node
from .utils import call_llm, get_embedding, get_rag_store, search_web_ddg


class DecideActionNode(Node):
    """LLM-based policy that decides whether to search, use RAG, or answer."""

    def prep(self, shared: Dict[str, Any]):
        return {
            "question": shared["question"],
            "context": shared.get("context", ""),
            "rag_results": shared.get("rag_results", []),
        }

    def exec(self, prep_res: Dict[str, Any]):
        print("🤔 DecideActionNode: Analyzing question and deciding next action (search/RAG/answer)")
        rag_context = "\n".join(
            f"- Source: {item['source']}\n  Excerpt: {item['text']}"
            for item in prep_res["rag_results"]
        )
        prompt = f"""
You orchestrate tools for a research agent.

QUESTION: {prep_res['question']}
SEARCH CONTEXT:\n{prep_res['context'] or 'none'}

RAG RESULTS:\n{rag_context or 'none'}

Decide the next action.
Return JSON with keys:
- action: search | rag | answer
- reason: short text
- search_query: string (required if action == "search")
- answer: string (required if action == "answer")
"""
        raw = call_llm(prompt)
        try:
            decision = json.loads(raw)
        except json.JSONDecodeError:
            decision = {"action": "rag", "reason": "fallback", "search_query": prep_res["question"]}
        return decision

    def post(self, shared, prep_res, exec_res):
        action = exec_res.get("action", "rag")
        if action == "search":
            shared["search_query"] = exec_res.get("search_query", shared["question"])
        elif action == "answer":
            shared["answer"] = exec_res.get("answer", "")
        return action


class SearchWebNode(Node):
    """Executes a web search to gather extra context."""

    def prep(self, shared):
        return shared.get("search_query", "")

    def exec(self, query: str):
        print(f"🔍 SearchWebNode: Performing web search for query: '{query}'")
        return search_web_ddg(query)

    def post(self, shared, prep_res, exec_res):
        snippets = []
        for result in exec_res:
            snippet = f"{result['title']} - {result['href']}\n{result['body']}"
            snippets.append(snippet)
        if snippets:
            shared["context"] = shared.get("context", "") + "\n\n".join(snippets)
        shared.setdefault("search_history", []).append(exec_res)
        shared.setdefault("metrics", {}).setdefault("search_count", 0)
        shared["metrics"]["search_count"] += 1
        return "decide"


class EmbedQueryNode(Node):
    """Embeds the user query using OpenAI embeddings."""

    def prep(self, shared):
        return shared["question"]

    def exec(self, question: str):
        print(f"🧮 EmbedQueryNode: Generating embedding vector for question: '{question}'")
        return get_embedding(question)

    def post(self, shared, prep_res, exec_res):
        shared["query_embedding"] = exec_res


class RetrieveRAGNode(Node):
    """Queries the FAISS index for relevant chunks."""

    def prep(self, shared):
        return shared.get("query_embedding")

    def exec(self, embedding):
        print("📚 RetrieveRAGNode: Searching FAISS index for relevant document chunks")
        if not embedding:
            return []
        store = get_rag_store()
        return store.search(embedding, top_k=3)

    def post(self, shared, prep_res, exec_res):
        shared["rag_results"] = exec_res
        shared.setdefault("metrics", {}).setdefault("rag_hits", 0)
        shared["metrics"]["rag_hits"] = len(exec_res)


class AnswerNode(Node):
    """Synthesizes a final answer via LLM."""

    def prep(self, shared):
        return {
            "question": shared["question"],
            "context": shared.get("context", ""),
            "rag_results": shared.get("rag_results", []),
        }

    def exec(self, prep_res):
        print("✍️ AnswerNode: Synthesizing final answer using LLM with context and RAG results")
        rag_section = "\n".join(
            f"Source: {item['source']}\nExcerpt: {item['text']}"
            for item in prep_res["rag_results"]
        )
        prompt = f"""
Answer the user's question using the research context and retrieved documents.
If uncertain, say so.

Question: {prep_res['question']}

Search Context:
{prep_res['context']}

Retrieved Documents:
{rag_section or 'None'}

Provide a concise answer and cite sources inline using (Source).
"""
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["answer"] = exec_res

