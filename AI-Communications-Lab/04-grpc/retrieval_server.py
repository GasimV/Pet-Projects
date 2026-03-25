"""
gRPC Retrieval Service

Searches a Qdrant vector database for the nearest neighbours of a query vector.
Falls back to mock results when Qdrant is unavailable.
"""

import uuid
from concurrent import futures

import grpc
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from generated import ai_services_pb2, ai_services_pb2_grpc

QDRANT_URL = "http://localhost:6333"
COLLECTION = "demo_docs"
PORT = 50052

# Sample documents to seed the collection
SEED_DOCS = [
    "Retrieval-Augmented Generation combines search with LLM generation.",
    "Vector embeddings represent text as dense numerical arrays.",
    "Cosine similarity measures the angle between two vectors.",
    "Qdrant is an open-source vector search engine written in Rust.",
    "gRPC uses HTTP/2 and Protocol Buffers for efficient RPC.",
]


class RetrievalServicer(ai_services_pb2_grpc.RetrievalServiceServicer):
    def __init__(self):
        self.qdrant = None
        try:
            self.qdrant = QdrantClient(url=QDRANT_URL, timeout=5)
            self.qdrant.get_collections()  # connectivity check
            self._ensure_collection()
            print("[retrieval-grpc] Qdrant connected")
        except Exception:
            self.qdrant = None
            print("[retrieval-grpc] Qdrant unavailable — mock mode")

    def _ensure_collection(self):
        """Create and seed the demo collection if it doesn't exist."""
        cols = [c.name for c in self.qdrant.get_collections().collections]
        if COLLECTION in cols:
            return
        # Use 64-dim mock vectors for seeding (real dims depend on model)
        self.qdrant.create_collection(
            COLLECTION, vectors_config=VectorParams(size=64, distance=Distance.COSINE)
        )
        import hashlib, math

        def _vec(t):
            h = hashlib.sha256(t.encode()).hexdigest()
            raw = [int(h[i:i+2], 16) / 255.0 for i in range(0, 128, 2)]
            norm = math.sqrt(sum(x*x for x in raw)) or 1.0
            return [x / norm for x in raw]

        points = [
            PointStruct(id=str(uuid.uuid4()), vector=_vec(doc), payload={"text": doc})
            for doc in SEED_DOCS
        ]
        self.qdrant.upsert(COLLECTION, points)
        print(f"[retrieval-grpc] Seeded {len(points)} docs")

    def Search(self, request, context):
        top_k = request.top_k or 3
        query_vec = list(request.query_vector)

        if self.qdrant:
            try:
                hits = self.qdrant.query_points(
                    collection_name=COLLECTION,
                    query=query_vec,
                    limit=top_k,
                ).points
                results = [
                    ai_services_pb2.SearchResult(
                        id=str(h.id),
                        text=h.payload.get("text", ""),
                        score=h.score,
                    )
                    for h in hits
                ]
                return ai_services_pb2.SearchResponse(results=results)
            except Exception as exc:
                context.set_details(str(exc))
                context.set_code(grpc.StatusCode.INTERNAL)
                return ai_services_pb2.SearchResponse()

        # Mock fallback
        mock = [
            ai_services_pb2.SearchResult(id="mock-1", text=SEED_DOCS[0], score=0.95),
            ai_services_pb2.SearchResult(id="mock-2", text=SEED_DOCS[1], score=0.87),
            ai_services_pb2.SearchResult(id="mock-3", text=SEED_DOCS[2], score=0.82),
        ]
        return ai_services_pb2.SearchResponse(results=mock[:top_k])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ai_services_pb2_grpc.add_RetrievalServiceServicer_to_server(
        RetrievalServicer(), server
    )
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    print(f"[retrieval-grpc] Listening on :{PORT}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
