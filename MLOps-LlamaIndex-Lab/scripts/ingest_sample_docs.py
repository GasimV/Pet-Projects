"""
Convenience script: ingest the sample documents into the vector store.

Usage:
    python scripts/ingest_sample_docs.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import PROJECT_ROOT
from app.rag.ingestion import ingest_documents, load_all_documents


def main():
    sample_dir = PROJECT_ROOT / "data" / "sample_docs"
    print(f"Loading documents from {sample_dir} …")
    docs = load_all_documents(sample_dir)
    print(f"Found {len(docs)} document(s). Starting ingestion …")
    ingest_documents(docs)
    print("Done.")


if __name__ == "__main__":
    main()
