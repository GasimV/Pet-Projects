"""
Text chunking utilities for RAG-Patterns-Lab.

Splits raw text into overlapping word-based chunks suitable
for embedding and storage in a vector database.
"""

from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 128,
    overlap: int = 32,
) -> list[str]:
    """Split *text* into word-based chunks with configurable overlap.

    Args:
        text: The input text to chunk.
        chunk_size: Maximum number of words per chunk.
        overlap: Number of overlapping words between consecutive chunks.

    Returns:
        A list of text chunks (strings).
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        # Advance by (chunk_size - overlap), but at least 1 word
        step = max(chunk_size - overlap, 1)
        start += step

    return chunks


def load_and_chunk(
    filepath: str,
    chunk_size: int = 128,
    overlap: int = 32,
) -> list[str]:
    """Read a text file and return word-based chunks.

    Args:
        filepath: Path to the text file.
        chunk_size: Maximum number of words per chunk.
        overlap: Number of overlapping words between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


# ── Quick self-test ─────────────────────────────────────────────────
if __name__ == "__main__":
    sample = "word " * 300  # 300 words
    chunks = chunk_text(sample.strip(), chunk_size=100, overlap=20)
    print(f"Input words : 300")
    print(f"Chunk size  : 100 words, overlap 20")
    print(f"Chunks made : {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  chunk {i}: {len(c.split())} words")
