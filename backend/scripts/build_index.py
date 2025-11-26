"""
Utility script to build the FAISS index used by the backend.
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import List

import faiss
import numpy as np

from agent.utils import fixed_size_chunk, get_embedding


def load_documents(doc_dir: Path) -> List[dict]:
    docs = []
    for path in doc_dir.glob("**/*"):
        if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
            continue
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def main():
    parser = argparse.ArgumentParser(description="Build the FAISS index for RAG.")
    parser.add_argument(
        "--docs",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "docs",
        help="Directory containing markdown/text documents.",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "index.faiss",
        help="Output FAISS index path.",
    )
    parser.add_argument(
        "--store-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "store.pkl",
        help="Metadata store path.",
    )
    parser.add_argument("--chunk-size", type=int, default=600)
    args = parser.parse_args()

    docs = load_documents(args.docs)
    if not docs:
        raise RuntimeError(f"No documents found in {args.docs}")

    chunks = []
    metadata = []
    for doc in docs:
        for idx, chunk in enumerate(fixed_size_chunk(doc["text"], args.chunk_size)):
            chunks.append(chunk)
            metadata.append({"source": doc["source"], "text": chunk})

    embeddings = []
    for chunk in chunks:
        embeddings.append(get_embedding(chunk))

    vectors = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    faiss.write_index(index, str(args.index_path))

    with args.store_path.open("wb") as f:
        pickle.dump({"items": metadata}, f)

    print(
        f"Wrote {len(metadata)} chunks to {args.index_path} "
        f"and metadata to {args.store_path}"
    )


if __name__ == "__main__":
    main()

