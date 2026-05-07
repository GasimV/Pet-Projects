"""Domain schema: object types, interface, unions, enums, inputs, scalars,
nested resolvers, deprecation, and Relay-style pagination.

The Query / Mutation / Subscription roots and the final `strawberry.Schema`
live in resolvers.py — split this way so each file has one purpose.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional, Union

import strawberry
from strawberry.scalars import JSON


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
@strawberry.enum
class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@strawberry.enum
class IngestionStatus(Enum):
    PENDING = "pending"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Interface + implementations
# ---------------------------------------------------------------------------
@strawberry.interface
class Model:
    id: strawberry.ID
    name: str
    provider: str


@strawberry.type
class ChatModel(Model):
    context_window: int
    supports_streaming: bool


@strawberry.type
class EmbeddingModel(Model):
    dimensions: int


# ---------------------------------------------------------------------------
# Domain types — nested resolvers use DataLoaders from `info.context`
# ---------------------------------------------------------------------------
@strawberry.type
class Embedding:
    vector: list[float]
    dimensions: int
    metadata: JSON  # JSON scalar — arbitrary structured metadata


@strawberry.type
class Tag:
    id: strawberry.ID
    name: str


@strawberry.type
class Chunk:
    id: strawberry.ID
    document_id: strawberry.ID
    content: str

    @strawberry.field
    async def embedding(self, info) -> Optional[Embedding]:
        return await info.context["embedding_loader"].load(self.id)


@strawberry.type
class Document:
    id: strawberry.ID
    title: str
    created_at: datetime  # DateTime scalar (auto)

    @strawberry.field
    async def chunks(self, info) -> list[Chunk]:
        return await info.context["chunks_loader"].load(self.id)

    @strawberry.field
    async def tags(self, info) -> list[Tag]:
        return await info.context["tags_loader"].load(self.id)


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class Message:
    id: strawberry.ID
    role: MessageRole
    content: str
    created_at: datetime
    tokens_used: Optional[int] = None
    # Private fields are kept out of the GraphQL schema but available
    # to resolvers for nested dispatch — `model_id` powers `model` below.
    model_id: strawberry.Private[Optional[str]] = None

    @strawberry.field
    async def model(self, info) -> Optional[Model]:
        if self.model_id is None:
            return None
        return await info.context["model_loader"].load(self.model_id)


@strawberry.type
class Conversation:
    id: strawberry.ID
    title: str
    created_at: datetime
    user_id: strawberry.Private[str]

    @strawberry.field
    async def user(self, info) -> Optional[User]:
        return await info.context["user_loader"].load(self.user_id)

    @strawberry.field
    async def messages(
        self,
        info,
        limit: int = 20,
        after: Optional[strawberry.ID] = None,
    ) -> list[Message]:
        msgs: list[Message] = await info.context["messages_loader"].load(self.id)
        if after is not None:
            idx = next((i for i, m in enumerate(msgs) if m.id == after), -1)
            msgs = msgs[idx + 1 :] if idx >= 0 else msgs
        return msgs[:limit]

    @strawberry.field(deprecation_reason="Use `title` instead — kept for old clients.")
    def summary(self) -> str:
        return self.title


# ---------------------------------------------------------------------------
# Union — search returns either a Document or a Chunk
# ---------------------------------------------------------------------------
SearchResult = Annotated[
    Union[Document, Chunk],
    strawberry.union("SearchResult"),
]


# ---------------------------------------------------------------------------
# Errors-as-data: typed mutation outcome
# ---------------------------------------------------------------------------
@strawberry.type
class ChatSuccess:
    message: Message
    conversation: Conversation


@strawberry.type
class RateLimitError:
    retry_after_seconds: int
    error_message: str


@strawberry.type
class ModelUnavailableError:
    model_name: str
    reason: str


ChatPayload = Annotated[
    Union[ChatSuccess, RateLimitError, ModelUnavailableError],
    strawberry.union("ChatPayload"),
]


# ---------------------------------------------------------------------------
# Pagination — Relay-style connection for documents
# ---------------------------------------------------------------------------
@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor: Optional[str]


@strawberry.type
class DocumentEdge:
    node: Document
    cursor: str


@strawberry.type
class DocumentConnection:
    edges: list[DocumentEdge]
    page_info: PageInfo
    total_count: int


# ---------------------------------------------------------------------------
# Misc payloads
# ---------------------------------------------------------------------------
@strawberry.type
class HealthStatus:
    status: str
    ollama_connected: bool
    chat_model: str
    embed_model: str


@strawberry.type
class TokenEvent:
    conversation_id: strawberry.ID
    token: str
    done: bool


@strawberry.type
class IngestionEvent:
    document_id: strawberry.ID
    status: IngestionStatus
    progress: float
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@strawberry.input
class SendMessageInput:
    conversation_id: strawberry.ID
    content: str
    model_id: Optional[strawberry.ID] = None


@strawberry.input
class UploadDocumentInput:
    title: str
    content: str
    tags: list[str] = strawberry.field(default_factory=list)
