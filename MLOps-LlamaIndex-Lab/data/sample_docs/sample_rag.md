# Retrieval-Augmented Generation (RAG)

## What is RAG?

Retrieval-Augmented Generation is a technique that enhances Large Language Models (LLMs) by providing them with relevant context retrieved from an external knowledge base before generating a response.

## How RAG Works

1. **Document Ingestion**: Documents are parsed, split into chunks, and converted to vector embeddings.
2. **Indexing**: Embeddings are stored in a vector database (e.g., Qdrant, Pinecone, Weaviate).
3. **Retrieval**: When a user asks a question, the query is embedded and the most similar document chunks are retrieved.
4. **Generation**: The retrieved chunks are passed as context to the LLM, which generates a grounded answer.

## Advantages

- Reduces hallucination by grounding answers in real documents.
- Keeps knowledge up-to-date without retraining the model.
- Provides source attribution for transparency.
- Works with any LLM — local or cloud-based.

## Common Frameworks

- **LlamaIndex**: Flexible data framework for connecting LLMs with external data.
- **LangChain**: General-purpose framework for building LLM applications.
- **Haystack**: End-to-end NLP framework with RAG support.
