"""
Utility script to build the Pinecone index used by the backend.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from pypdf import PdfReader

from agent.utils import fixed_size_chunk, get_embedding

load_dotenv()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Warning: Failed to extract text from {pdf_path.name}: {e}")
        return ""


def load_documents(doc_dir: Path) -> List[dict]:
    """Load documents from markdown, text, and PDF files."""
    docs = []
    for path in doc_dir.glob("**/*"):
        if not path.is_file():
            continue
        
        # Handle different file types
        if path.suffix.lower() in {".md", ".txt"}:
            try:
                text = path.read_text(encoding="utf-8")
                docs.append({"source": path.name, "text": text})
            except Exception as e:
                print(f"Warning: Failed to read {path.name}: {e}")
        
        elif path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(path)
            if text:
                docs.append({"source": path.name, "text": text})
    
    return docs


def main():
    parser = argparse.ArgumentParser(description="Build the Pinecone index for RAG.")
    parser.add_argument(
        "--docs",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "docs",
        help="Directory containing markdown/text documents.",
    )
    parser.add_argument(
        "--index-name",
        type=str,
        default=os.getenv("PINECONE_INDEX_NAME", "mainagent-rag"),
        help="Pinecone index name.",
    )
    parser.add_argument("--chunk-size", type=int, default=600)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of vectors to upsert at once.",
    )
    args = parser.parse_args()

    # Initialize Pinecone
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY is not set in environment variables")

    pc = Pinecone(api_key=api_key)

    # Check if index exists, create if not
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    
    if args.index_name not in existing_indexes:
        dimension = int(os.getenv("PINECONE_DIMENSION", "1536"))
        print(f"Creating new Pinecone index '{args.index_name}' with dimension {dimension}...")
        
        pc.create_index(
            name=args.index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=os.getenv("PINECONE_CLOUD", "aws"),
                region=os.getenv("PINECONE_REGION", "us-east-1")
            )
        )
        print(f"Index '{args.index_name}' created successfully!")
    else:
        print(f"Using existing index '{args.index_name}'")

    index = pc.Index(args.index_name)

    # Load and process documents
    docs = load_documents(args.docs)
    if not docs:
        raise RuntimeError(f"No documents found in {args.docs}")

    print(f"Found {len(docs)} documents. Processing chunks...")

    # Prepare vectors for upsert
    vectors_to_upsert = []
    chunk_id = 0

    for doc in docs:
        chunks = fixed_size_chunk(doc["text"], args.chunk_size)
        print(f"Processing '{doc['source']}': {len(chunks)} chunks")
        
        for chunk in chunks:
            # Generate embedding
            embedding = get_embedding(chunk)
            
            # Create vector with metadata
            vector = {
                "id": f"chunk_{chunk_id}",
                "values": embedding,
                "metadata": {
                    "source": doc["source"],
                    "text": chunk
                }
            }
            vectors_to_upsert.append(vector)
            chunk_id += 1

            # Upsert in batches
            if len(vectors_to_upsert) >= args.batch_size:
                index.upsert(vectors=vectors_to_upsert)
                print(f"Upserted {len(vectors_to_upsert)} vectors (total: {chunk_id})")
                vectors_to_upsert = []

    # Upsert remaining vectors
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        print(f"Upserted final {len(vectors_to_upsert)} vectors")

    print(f"\n✅ Successfully indexed {chunk_id} chunks to Pinecone index '{args.index_name}'")
    
    # Print index stats
    stats = index.describe_index_stats()
    print(f"Index stats: {stats}")


if __name__ == "__main__":
    main()

