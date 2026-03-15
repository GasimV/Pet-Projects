# RAG-Patterns-Lab

A hands-on Python repository demonstrating two retrieval-augmented generation (RAG) architectures side by side:

1. **Standard RAG** — semantic search with Qdrant
2. **GraphRAG** — semantic search with Qdrant + graph-based context expansion with Neo4j

Built for learning, experimentation, and portfolio use.

---

## Why This Repo Exists

RAG is the dominant pattern for grounding LLM responses in external knowledge, but a single vector search can miss structurally related context. This project shows, with real runnable code, how adding a graph layer (GraphRAG) addresses that gap — and how even Qdrant's payload metadata can model lightweight adjacency.

---

## Architectures

### Standard RAG (Qdrant only)

```
Query → Embed → Qdrant similarity search → Top-k chunks → LLM
```

The system embeds a query, searches a Qdrant collection for the most semantically similar chunks, and returns them as context. This is fast, simple, and effective for most retrieval tasks.

### GraphRAG (Qdrant + Neo4j)

```
Query → Embed → Qdrant similarity search → Top chunk ID
                                              ↓
                              Neo4j graph traversal (NEXT / PREVIOUS / SAME_DOCUMENT)
                                              ↓
                              Expanded context chunks → LLM
```

After Qdrant returns the best semantic match, Neo4j is used to traverse relationships and pull in adjacent or related chunks. This captures context that vector similarity alone might miss — especially useful for multi-hop reasoning or when relevant information uses different wording.

### Why Both?

| Aspect | Qdrant payloads | Neo4j |
|---|---|---|
| Adjacency tracking | Stores `previous_chunk_id` / `next_chunk_id` in payload metadata | Native `NEXT` / `PREVIOUS` / `SAME_DOCUMENT` edges |
| Multi-hop traversal | Requires multiple queries | Single Cypher query with variable-length paths |
| Schema flexibility | Arbitrary JSON, no enforced schema | Property graph with labels and typed relationships |
| Best for | Lightweight adjacency, filtering | Rich relationship queries, knowledge graphs |

Qdrant's payload system can model simple graph-like adjacency — and this project demonstrates that. But for native traversal, path queries, and complex relationship patterns, a dedicated graph database like Neo4j is the right tool.

---

## Project Structure

```
RAG-Patterns-Lab/
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── docker-compose.yml
│
├── data/
│   └── documents.txt          # Sample corpus about RAG, vector DBs, GraphRAG
│
├── embeddings/
│   ├── __init__.py
│   └── embedder.py            # BAAI/bge-m3 embedding wrapper
│
├── utils/
│   ├── __init__.py
│   ├── config.py              # .env loader and project constants
│   └── chunking.py            # Word-based text chunker with overlap
│
├── rag_qdrant/
│   ├── __init__.py
│   ├── create_collection.py   # Create Qdrant collection
│   ├── ingest.py              # Chunk → embed → upsert into Qdrant
│   └── query.py               # Semantic search demo
│
└── graph_rag/
    ├── __init__.py
    ├── build_graph.py          # Build chunk graph in Neo4j
    ├── graph_retrieval.py      # Neo4j traversal helpers
    └── query_graph_rag.py      # Full GraphRAG pipeline demo
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Embeddings | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) via sentence-transformers |
| Vector DB | [Qdrant](https://qdrant.tech/) |
| Graph DB | [Neo4j](https://neo4j.com/) Community Edition |
| Infra | Docker Compose |
| Config | python-dotenv |

---

## Setup

### Prerequisites

- Python 3.10+
- Docker Desktop (for Qdrant and Neo4j)
- Git
- (Optional) NVIDIA GPU with CUDA for faster embeddings

### 1. Clone the repository

```bash
git clone https://github.com/GasimV/Pet-Projects/RAG-Patterns-Lab.git
cd RAG-Patterns-Lab
```

### 2. Start Docker services

```bash
docker-compose up -d
```

This starts:
- **Qdrant** on `localhost:6333` (dashboard at `http://localhost:6333/dashboard`)
- **Neo4j** on `localhost:7474` (browser) and `localhost:7687` (Bolt)

### 3. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# CMD
.\.venv\Scripts\activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**GPU support (optional):** If you have a CUDA-capable GPU, install PyTorch with CUDA before the requirements:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

If no GPU is available, sentence-transformers will default to CPU automatically.

### 5. Configure environment variables

```bash
copy .env.example .env
```

Edit `.env` if your Qdrant/Neo4j settings differ from the defaults.

---

## Usage

All scripts are run as Python modules from the repository root.

### Standard RAG Pipeline

```bash
# 1. Create the Qdrant collection
python -m rag_qdrant.create_collection

# 2. Ingest documents (chunk → embed → upsert)
python -m rag_qdrant.ingest

# 3. Run a sample query
python -m rag_qdrant.query
```

### GraphRAG Pipeline

```bash
# 1. Build the Neo4j graph (uses the same chunks as Qdrant)
python -m graph_rag.build_graph

# 2. Run the GraphRAG query (Qdrant search + Neo4j expansion)
python -m graph_rag.query_graph_rag
```

---

## Example Output

### Standard RAG query

```
======================================================================
  QUERY: How does GraphRAG improve retrieval compared to standard RAG?
======================================================================

── Result 1  (score: 0.8742) ──
  Chunk ID    : 5
  Chunk Index : 5
  Source      : documents.txt
  Prev / Next : 4 / 6
  Text        : GraphRAG is an advanced retrieval pattern that combines ...

── Result 2  (score: 0.8519) ──
  Chunk ID    : 6
  Chunk Index : 6
  ...
```

### GraphRAG query

```
======================================================================
  GRAPH-RAG QUERY
======================================================================

  Query: How does GraphRAG improve retrieval compared to standard RAG?

── Step 1: Qdrant semantic search ──
  Top hit   : chunk 5  (score: 0.8742)
  Text      : GraphRAG is an advanced retrieval pattern ...

── Step 2: Neo4j graph expansion ──

  PREVIOUS chunks (2):
    chunk 4: Neo4j is the most widely adopted graph database ...
    chunk 3: Graph databases store data as nodes, edges ...

  NEXT chunks (2):
    chunk 6: The key advantage of GraphRAG over standard RAG ...
    chunk 7: Embedding models convert text into dense numerical ...

  SAME_DOCUMENT siblings: 8 chunk(s)

── Combined context chunk IDs: [3, 4, 5, 6, 7]
```

The GraphRAG pipeline retrieves the same top chunk as standard RAG, then expands context via Neo4j to include adjacent chunks — giving a downstream LLM a more complete picture.

---

## Concepts

### Text Chunking

Documents are split into overlapping word-based segments. Overlap ensures that no information is lost at chunk boundaries. The same chunking logic is shared between both pipelines for consistency.

### Qdrant Payload Adjacency

Each Qdrant point stores `previous_chunk_id` and `next_chunk_id` in its payload. This allows lightweight graph-like traversal using Qdrant alone — useful when you want basic adjacency without a separate graph database.

### Neo4j Graph Traversal

Neo4j stores the same chunks as nodes with `NEXT`, `PREVIOUS`, and `SAME_DOCUMENT` relationships. Cypher queries can traverse variable-length paths in a single query, making multi-hop context expansion efficient and expressive.

---

## Future Improvements

- Add an LLM generation step (e.g., OpenAI or local model) to complete the RAG loop
- Implement entity extraction to create richer knowledge graph relationships
- Add hybrid search (sparse + dense) using Qdrant's built-in support
- Benchmark retrieval quality: Standard RAG vs. GraphRAG on evaluation datasets
- Add a Streamlit or Gradio UI for interactive querying
- Support multiple documents with per-document metadata
- Add RELATED edges based on semantic similarity between non-adjacent chunks

---

## License

MIT — free for personal and commercial use.
