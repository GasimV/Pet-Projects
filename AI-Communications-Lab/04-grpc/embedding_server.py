"""
gRPC Embedding Service

Wraps Ollama's bge-m3 embedding model behind a gRPC interface.
Falls back to a deterministic mock embedding when Ollama is unavailable.
"""

import hashlib
import math
from concurrent import futures

import grpc
import httpx

# --- Import generated stubs (run generate_proto.py first) ---
from generated import ai_services_pb2, ai_services_pb2_grpc

OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "bge-m3:latest"
PORT = 50051


def _mock_embedding(text: str, dims: int = 64) -> list[float]:
    """Deterministic pseudo-embedding based on text hash."""
    h = hashlib.sha256(text.encode()).hexdigest()
    raw = [int(h[i : i + 2], 16) / 255.0 for i in range(0, min(len(h), dims * 2), 2)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


class EmbeddingServicer(ai_services_pb2_grpc.EmbeddingServiceServicer):
    def __init__(self):
        self.ollama_ok = self._probe()
        status = "connected" if self.ollama_ok else "mock mode"
        print(f"[embed-grpc] Ollama {status}")

    @staticmethod
    def _probe() -> bool:
        try:
            r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
            return r.status_code == 200
        except httpx.ConnectError:
            return False

    def Embed(self, request, context):
        if self.ollama_ok:
            try:
                r = httpx.post(
                    f"{OLLAMA_BASE}/api/embed",
                    json={"model": EMBED_MODEL, "input": request.text},
                    timeout=30,
                )
                r.raise_for_status()
                vec = r.json()["embeddings"][0]
                return ai_services_pb2.EmbedResponse(
                    vector=vec, dimensions=len(vec), model=EMBED_MODEL
                )
            except Exception as exc:
                context.set_details(str(exc))
                context.set_code(grpc.StatusCode.INTERNAL)
                return ai_services_pb2.EmbedResponse()

        vec = _mock_embedding(request.text)
        return ai_services_pb2.EmbedResponse(
            vector=vec, dimensions=len(vec), model="mock"
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ai_services_pb2_grpc.add_EmbeddingServiceServicer_to_server(
        EmbeddingServicer(), server
    )
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    print(f"[embed-grpc] Listening on :{PORT}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
