from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.generated"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = Field(default="voice-agent-platform", alias="PROJECT_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    runtime_profile: str = Field(default="local-cpu", alias="RUNTIME_PROFILE")
    gateway_host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")
    gateway_port: int = Field(default=8080, alias="GATEWAY_PORT")
    orchestrator_grpc_host: str = Field(default="localhost", alias="ORCHESTRATOR_GRPC_HOST")
    orchestrator_grpc_port: int = Field(default=50051, alias="ORCHESTRATOR_GRPC_PORT")
    orchestrator_http_port: int = Field(default=8081, alias="ORCHESTRATOR_HTTP_PORT")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    postgres_dsn: str = Field(
        default="postgresql+asyncpg://voice:voice@localhost:5432/voice_platform",
        alias="POSTGRES_DSN",
    )
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    livekit_url: str = Field(default="ws://localhost:7880", alias="LIVEKIT_URL")
    livekit_api_key: str = Field(default="devkey", alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="secret", alias="LIVEKIT_API_SECRET")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_chat_model: str = Field(default="gemma3:270m", alias="OLLAMA_CHAT_MODEL")
    ollama_embed_model: str = Field(default="bge-m3:latest", alias="OLLAMA_EMBED_MODEL")
    ollama_tts_model: str = Field(default="", alias="OLLAMA_TTS_MODEL")
    enable_ollama: bool = Field(default=True, alias="ENABLE_OLLAMA")
    enable_vllm: bool = Field(default=False, alias="ENABLE_VLLM")
    vllm_base_url: str = Field(default="http://localhost:8000/v1", alias="VLLM_BASE_URL")
    vllm_model: str = Field(default="TinyLlama/TinyLlama-1.1B-Chat-v1.0", alias="VLLM_MODEL")
    stt_model: str = Field(default="tiny.en", alias="STT_MODEL")
    stt_device: str = Field(default="cpu", alias="STT_DEVICE")
    stt_compute_type: str = Field(default="int8", alias="STT_COMPUTE_TYPE")
    stt_chunk_ms: int = Field(default=250, alias="STT_CHUNK_MS")
    tts_provider: str = Field(default="espeak", alias="TTS_PROVIDER")
    tts_voice: str = Field(default="en-us", alias="TTS_VOICE")
    temporal_target: str = Field(default="localhost:7233", alias="TEMPORAL_TARGET")
    temporal_namespace: str = Field(default="default", alias="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(default="voice-platform", alias="TEMPORAL_TASK_QUEUE")
    knowledge_dir: str = Field(default="knowledge", alias="KNOWLEDGE_DIR")
    default_domain_pack: str = Field(default="starship", alias="DEFAULT_DOMAIN_PACK")
    session_event_channel: str = Field(default="voice-platform.session-events", alias="SESSION_EVENT_CHANNEL")
    session_stream_prefix: str = Field(default="voice-platform:session", alias="SESSION_STREAM_PREFIX")
    otel_exporter_otlp_endpoint: str | None = Field(default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()

