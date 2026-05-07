"""Root Query, Mutation, Subscription + DataLoader factories + final Schema.

DataLoaders are created per-request via `make_loaders()`, called by the
FastAPI context_getter on each connection. This is the canonical way to
avoid N+1 queries — each loader batches `.load()` calls within one event
loop tick.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import strawberry
from strawberry.dataloader import DataLoader

import ollama
from data import (
    CHAT_MODELS,
    CHUNKS_BY_DOCUMENT,
    CONVERSATIONS,
    DOCUMENT_TAGS,
    DOCUMENTS,
    EMBEDDING_MODELS,
    EMBEDDINGS_BY_CHUNK,
    MESSAGES_BY_CONVERSATION,
    TAGS,
    USERS,
)
from schema import (
    ChatModel,
    ChatPayload,
    ChatSuccess,
    Chunk,
    Conversation,
    Document,
    DocumentConnection,
    DocumentEdge,
    Embedding,
    EmbeddingModel,
    HealthStatus,
    IngestionEvent,
    IngestionStatus,
    Message,
    MessageRole,
    Model,
    ModelUnavailableError,
    PageInfo,
    RateLimitError,
    SearchResult,
    SendMessageInput,
    Tag,
    TokenEvent,
    UploadDocumentInput,
    User,
)


# ---------------------------------------------------------------------------
# Dict → strawberry-type converters (kept here so resolvers and loaders share)
# ---------------------------------------------------------------------------
def _to_user(d: dict) -> User:
    return User(id=d["id"], name=d["name"], email=d["email"])


def _to_model(d: dict) -> Model:
    if "context_window" in d:
        return ChatModel(
            id=d["id"],
            name=d["name"],
            provider=d["provider"],
            context_window=d["context_window"],
            supports_streaming=d["supports_streaming"],
        )
    return EmbeddingModel(
        id=d["id"],
        name=d["name"],
        provider=d["provider"],
        dimensions=d["dimensions"],
    )


def _to_message(d: dict) -> Message:
    return Message(
        id=d["id"],
        role=MessageRole(d["role"]),
        content=d["content"],
        created_at=d["created_at"],
        tokens_used=d.get("tokens_used"),
        model_id=d.get("model_id"),
    )


def _to_chunk(d: dict) -> Chunk:
    return Chunk(id=d["id"], document_id=d["document_id"], content=d["content"])


def _to_tag(d: dict) -> Tag:
    return Tag(id=d["id"], name=d["name"])


def _to_document(d: dict) -> Document:
    return Document(id=d["id"], title=d["title"], created_at=d["created_at"])


def _to_conversation(d: dict) -> Conversation:
    return Conversation(
        id=d["id"],
        title=d["title"],
        created_at=d["created_at"],
        user_id=d["user_id"],
    )


# ---------------------------------------------------------------------------
# DataLoader load functions — each receives a list of keys, returns parallel results
# ---------------------------------------------------------------------------
async def _load_users(keys: list[str]) -> list[Optional[User]]:
    return [_to_user(USERS[k]) if k in USERS else None for k in keys]


async def _load_models(keys: list[str]) -> list[Optional[Model]]:
    out: list[Optional[Model]] = []
    for k in keys:
        if k in CHAT_MODELS:
            out.append(_to_model(CHAT_MODELS[k]))
        elif k in EMBEDDING_MODELS:
            out.append(_to_model(EMBEDDING_MODELS[k]))
        else:
            out.append(None)
    return out


async def _load_messages_by_conversation(keys: list[str]) -> list[list[Message]]:
    return [
        [_to_message(m) for m in MESSAGES_BY_CONVERSATION.get(k, [])]
        for k in keys
    ]


async def _load_chunks_by_document(keys: list[str]) -> list[list[Chunk]]:
    return [[_to_chunk(c) for c in CHUNKS_BY_DOCUMENT.get(k, [])] for k in keys]


async def _load_tags_by_document(keys: list[str]) -> list[list[Tag]]:
    return [
        [_to_tag(TAGS[t]) for t in DOCUMENT_TAGS.get(k, []) if t in TAGS]
        for k in keys
    ]


async def _load_embeddings_by_chunk(keys: list[str]) -> list[Optional[Embedding]]:
    out: list[Optional[Embedding]] = []
    for k in keys:
        e = EMBEDDINGS_BY_CHUNK.get(k)
        if e is None:
            out.append(None)
        else:
            out.append(
                Embedding(
                    vector=e["vector"],
                    dimensions=e["dimensions"],
                    metadata=e["metadata"],
                )
            )
    return out


def make_loaders() -> dict:
    """Per-request DataLoader bundle. Called by the FastAPI context_getter."""
    return {
        "user_loader": DataLoader(load_fn=_load_users),
        "model_loader": DataLoader(load_fn=_load_models),
        "messages_loader": DataLoader(load_fn=_load_messages_by_conversation),
        "chunks_loader": DataLoader(load_fn=_load_chunks_by_document),
        "tags_loader": DataLoader(load_fn=_load_tags_by_document),
        "embedding_loader": DataLoader(load_fn=_load_embeddings_by_chunk),
    }


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> HealthStatus:
        return HealthStatus(
            status="ok",
            ollama_connected=ollama.is_available(),
            chat_model=ollama.CHAT_MODEL,
            embed_model=ollama.EMBED_MODEL,
        )

    @strawberry.field
    def models(self) -> list[Model]:
        return [_to_model(m) for m in CHAT_MODELS.values()] + [
            _to_model(m) for m in EMBEDDING_MODELS.values()
        ]

    @strawberry.field
    def conversation(self, id: strawberry.ID) -> Optional[Conversation]:
        c = CONVERSATIONS.get(id)
        return _to_conversation(c) if c else None

    @strawberry.field
    def conversations(
        self, limit: int = 10, offset: int = 0
    ) -> list[Conversation]:
        items = list(CONVERSATIONS.values())
        return [_to_conversation(c) for c in items[offset : offset + limit]]

    @strawberry.field
    def documents(
        self, first: int = 5, after: Optional[str] = None
    ) -> DocumentConnection:
        items = sorted(DOCUMENTS.values(), key=lambda d: d["id"])
        start = 0
        if after is not None:
            try:
                start = next(i for i, d in enumerate(items) if d["id"] == after) + 1
            except StopIteration:
                start = 0
        page = items[start : start + first]
        edges = [DocumentEdge(node=_to_document(d), cursor=d["id"]) for d in page]
        return DocumentConnection(
            edges=edges,
            page_info=PageInfo(
                has_next_page=(start + first) < len(items),
                end_cursor=page[-1]["id"] if page else None,
            ),
            total_count=len(items),
        )

    @strawberry.field
    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        q = query.lower()
        out: list[SearchResult] = []
        for d in DOCUMENTS.values():
            if q in d["title"].lower():
                out.append(_to_document(d))
        for chunks in CHUNKS_BY_DOCUMENT.values():
            for ch in chunks:
                if q in ch["content"].lower():
                    out.append(_to_chunk(ch))
        return out[:limit]


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_conversation(
        self, title: str, user_id: strawberry.ID = strawberry.ID("u1")
    ) -> Conversation:
        new_id = f"c-{uuid.uuid4().hex[:8]}"
        rec = {
            "id": new_id,
            "title": title,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        }
        CONVERSATIONS[new_id] = rec
        MESSAGES_BY_CONVERSATION[new_id] = []
        return _to_conversation(rec)

    @strawberry.mutation
    async def send_message(self, input: SendMessageInput) -> ChatPayload:
        # Errors-as-data: missing conversation
        if input.conversation_id not in CONVERSATIONS:
            return ModelUnavailableError(
                model_name=input.model_id or ollama.CHAT_MODEL,
                reason=f"Conversation {input.conversation_id} not found",
            )

        # Errors-as-data: simulated rate limit on a magic word
        if input.content.strip().lower() == "rate-limit":
            return RateLimitError(
                retry_after_seconds=30,
                error_message="Slow down — try again in 30 seconds.",
            )

        # Persist user message
        user_msg = {
            "id": f"msg-{uuid.uuid4().hex[:6]}",
            "role": "user",
            "content": input.content,
            "tokens_used": None,
            "model_id": None,
            "created_at": datetime.now(timezone.utc),
        }
        MESSAGES_BY_CONVERSATION[input.conversation_id].append(user_msg)

        # Generate reply
        try:
            reply_text = await ollama.chat(input.content)
        except Exception as exc:  # noqa: BLE001
            return ModelUnavailableError(
                model_name=ollama.CHAT_MODEL, reason=str(exc)
            )

        asst_msg = {
            "id": f"msg-{uuid.uuid4().hex[:6]}",
            "role": "assistant",
            "content": reply_text,
            "tokens_used": len(reply_text.split()),
            "model_id": "m-gemma",
            "created_at": datetime.now(timezone.utc),
        }
        MESSAGES_BY_CONVERSATION[input.conversation_id].append(asst_msg)

        return ChatSuccess(
            message=_to_message(asst_msg),
            conversation=_to_conversation(CONVERSATIONS[input.conversation_id]),
        )

    @strawberry.mutation
    async def embed_text(self, text: str) -> Embedding:
        vec = await ollama.embed(text)
        return Embedding(
            vector=vec, dimensions=len(vec), metadata={"text_length": len(text)}
        )

    @strawberry.mutation
    def upload_document(self, input: UploadDocumentInput) -> Document:
        new_id = f"d-{uuid.uuid4().hex[:8]}"
        DOCUMENTS[new_id] = {
            "id": new_id,
            "title": input.title,
            "created_at": datetime.now(timezone.utc),
        }
        # Naive sentence-based chunking — good enough for a demo
        sentences = [s.strip() for s in input.content.split(".") if s.strip()]
        CHUNKS_BY_DOCUMENT[new_id] = [
            {
                "id": f"ch-{uuid.uuid4().hex[:6]}",
                "document_id": new_id,
                "content": s,
            }
            for s in sentences
        ]
        # Resolve tag names → IDs (creating new tags as needed)
        tag_ids: list[str] = []
        for name in input.tags:
            existing = next(
                (tid for tid, t in TAGS.items() if t["name"] == name), None
            )
            if existing:
                tag_ids.append(existing)
            else:
                new_tid = f"t-{uuid.uuid4().hex[:6]}"
                TAGS[new_tid] = {"id": new_tid, "name": name}
                tag_ids.append(new_tid)
        DOCUMENT_TAGS[new_id] = tag_ids
        return _to_document(DOCUMENTS[new_id])


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------
@strawberry.type
class Subscription:
    @strawberry.subscription
    async def token_stream(
        self, conversation_id: strawberry.ID, message: str
    ) -> AsyncGenerator[TokenEvent, None]:
        async for token, done in ollama.stream_tokens(message):
            yield TokenEvent(
                conversation_id=conversation_id, token=token, done=done
            )
            if done:
                return

    @strawberry.subscription
    async def ingestion_status(
        self, document_id: strawberry.ID
    ) -> AsyncGenerator[IngestionEvent, None]:
        steps = [
            (IngestionStatus.PENDING, 0.0, "Queued"),
            (IngestionStatus.PARSING, 0.25, "Parsing document"),
            (IngestionStatus.EMBEDDING, 0.6, "Generating embeddings"),
            (IngestionStatus.COMPLETED, 1.0, "Done"),
        ]
        for status, progress, msg in steps:
            yield IngestionEvent(
                document_id=document_id,
                status=status,
                progress=progress,
                message=msg,
            )
            await asyncio.sleep(0.4)


# ---------------------------------------------------------------------------
# Final schema. `types=` forces interface implementations and union members
# into the schema even when they're not directly referenced from a root field.
# ---------------------------------------------------------------------------
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    types=[
        ChatModel,
        EmbeddingModel,
        Document,
        Chunk,
        ChatSuccess,
        RateLimitError,
        ModelUnavailableError,
    ],
)
