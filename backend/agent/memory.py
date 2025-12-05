"""
Memory utilities for MainAgent conversation memory using Pinecone.
Provides both short-term (sliding window) and long-term (Pinecone-indexed) memory.
"""

from typing import List, Dict, Any, Tuple, Optional
from pinecone import Pinecone
import os
import time
from .utils import get_embedding


def get_memory_index(index_name: str = None):
    """
    Get or create a Pinecone index for conversation memory.
    
    Args:
        index_name: Name of the Pinecone index (defaults to env var or 'mainagent-memory')
        
    Returns:
        Pinecone index instance
    """
    if index_name is None:
        index_name = os.getenv("PINECONE_MEMORY_INDEX", "mainagent-memory")
    
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set")
    
    pc = Pinecone(api_key=api_key)
    
    # Check if index exists
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        # Create serverless index for memory
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI embedding dimension
            metric="cosine",
            spec={
                "serverless": {
                    "cloud": os.getenv("PINECONE_CLOUD", "aws"),
                    "region": os.getenv("PINECONE_REGION", "us-east-1")
                }
            }
        )
        # Wait for index to be ready
        time.sleep(1)
    
    return pc.Index(index_name)


def add_to_memory(
    index,
    session_id: str,
    conversation: List[Dict[str, str]],
    embedding: List[float],
    conversation_id: str = None
) -> str:
    """
    Add a conversation to Pinecone memory.
    
    Args:
        index: Pinecone index instance
        session_id: User session identifier
        conversation: List of message dicts with 'role' and 'content'
        embedding: Vector embedding of the conversation
        conversation_id: Optional unique ID (auto-generated if not provided)
        
    Returns:
        ID of the stored conversation
    """
    if conversation_id is None:
        conversation_id = f"{session_id}_{int(time.time() * 1000)}"
    
    # Prepare metadata
    user_msg = next((msg for msg in conversation if msg["role"] == "user"), {"content": ""})
    assistant_msg = next((msg for msg in conversation if msg["role"] == "assistant"), {"content": ""})
    
    metadata = {
        "session_id": session_id,
        "user_message": user_msg["content"][:1000],  # Pinecone metadata limit
        "assistant_message": assistant_msg["content"][:1000],
        "timestamp": int(time.time()),
        "type": "conversation_memory"
    }
    
    # Upsert to Pinecone
    index.upsert(vectors=[(conversation_id, embedding, metadata)])
    
    return conversation_id


def retrieve_from_memory(
    index,
    session_id: str,
    query: str,
    k: int = 1
) -> Optional[Tuple[List[Dict[str, str]], float]]:
    """
    Retrieve the most relevant past conversation from Pinecone memory.
    
    Args:
        index: Pinecone index instance
        session_id: User session identifier
        query: Current user query
        k: Number of results to return (default: 1)
        
    Returns:
        Tuple of (conversation, score) or None if no memories exist
    """
    # Generate embedding for query
    query_embedding = get_embedding(query)
    
    # Query Pinecone with session filter
    results = index.query(
        vector=query_embedding,
        top_k=k,
        filter={"session_id": session_id, "type": "conversation_memory"},
        include_metadata=True
    )
    
    if not results.matches:
        return None
    
    # Get the best match
    best_match = results.matches[0]
    
    # Reconstruct conversation from metadata
    conversation = [
        {"role": "user", "content": best_match.metadata["user_message"]},
        {"role": "assistant", "content": best_match.metadata["assistant_message"]}
    ]
    
    return (conversation, float(best_match.score))


def embed_conversation(conversation: List[Dict[str, str]]) -> List[float]:
    """
    Create an embedding for a conversation pair.
    
    Args:
        conversation: List of 2 messages (user and assistant)
        
    Returns:
        Embedding vector
    """
    # Extract user and assistant messages
    user_msg = next((msg for msg in conversation if msg["role"] == "user"), {"content": ""})
    assistant_msg = next((msg for msg in conversation if msg["role"] == "assistant"), {"content": ""})
    
    # Combine into single text
    combined = f"User: {user_msg['content']} Assistant: {assistant_msg['content']}"
    
    # Generate and return embedding
    return get_embedding(combined)


def should_archive_memory(messages: List[Dict[str, str]], window_size: int = 6) -> bool:
    """
    Check if we should archive old messages to long-term memory.
    
    Args:
        messages: Current message list
        window_size: Maximum messages to keep in short-term memory
        
    Returns:
        True if archiving is needed
    """
    return len(messages) > window_size


def extract_oldest_pair(messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Extract the oldest conversation pair from messages.
    
    Args:
        messages: Current message list
        
    Returns:
        Tuple of (oldest_pair, remaining_messages)
    """
    if len(messages) < 2:
        return ([], messages)
    
    oldest_pair = messages[:2]
    remaining = messages[2:]
    
    return (oldest_pair, remaining)


def clear_session_memory(index, session_id: str):
    """
    Clear all memory for a specific session.
    
    Args:
        index: Pinecone index instance
        session_id: User session identifier
    """
    # Note: Pinecone doesn't support delete by metadata filter directly
    # You would need to query all vectors for the session and delete by IDs
    # This is a placeholder for the implementation
    pass


def get_memory_stats(index, session_id: str) -> Dict[str, Any]:
    """
    Get statistics about stored memories for a session.
    
    Args:
        index: Pinecone index instance
        session_id: User session identifier
        
    Returns:
        Dictionary with memory statistics
    """
    # Query to count memories
    results = index.query(
        vector=[0.0] * 1536,  # Dummy vector
        top_k=10000,  # Large number to get all
        filter={"session_id": session_id, "type": "conversation_memory"},
        include_metadata=False
    )
    
    return {
        "session_id": session_id,
        "total_memories": len(results.matches),
        "index_name": index._config.host.split('.')[0]
    }
