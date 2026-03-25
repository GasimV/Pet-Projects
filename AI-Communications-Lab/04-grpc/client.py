"""
gRPC Gateway Client

Demonstrates calling both the Embedding and Retrieval gRPC services
in sequence — the typical "embed then search" pattern used in RAG.
"""

import grpc
from generated import ai_services_pb2, ai_services_pb2_grpc

EMBED_ADDR = "localhost:50051"
RETRIEVAL_ADDR = "localhost:50052"


def run(query: str = "What is RAG?"):
    print(f"Query: {query}\n")

    # Step 1: Get embedding
    with grpc.insecure_channel(EMBED_ADDR) as ch:
        stub = ai_services_pb2_grpc.EmbeddingServiceStub(ch)
        resp = stub.Embed(ai_services_pb2.EmbedRequest(text=query))
        print(f"Embedding: {resp.dimensions} dims (model={resp.model})")
        vector = list(resp.vector)

    # Step 2: Search with embedding
    with grpc.insecure_channel(RETRIEVAL_ADDR) as ch:
        stub = ai_services_pb2_grpc.RetrievalServiceStub(ch)
        resp = stub.Search(
            ai_services_pb2.SearchRequest(query_vector=vector, top_k=3)
        )
        print(f"\nTop {len(resp.results)} results:")
        for r in resp.results:
            print(f"  [{r.score:.3f}] {r.text}")


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "What is RAG?"
    run(query)
