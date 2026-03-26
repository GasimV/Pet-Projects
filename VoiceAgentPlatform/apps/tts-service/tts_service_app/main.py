from __future__ import annotations

import asyncio
import logging
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
for rel in (
    ROOT / "libs" / "shared-config",
    ROOT / "libs" / "shared-observability",
    ROOT / "libs" / "proto" / "generated",
):
    rel_str = str(rel)
    if rel_str not in sys.path:
        sys.path.insert(0, rel_str)

import grpc
import uvicorn

from shared_config.settings import get_settings
from shared_observability.logging import configure_logging
from shared_observability.tracing import configure_tracing
from tts_service_app.grpc_server import TextToSpeechService
from tts_service_app.http_app import app
from tts_service_app.providers import EspeakProvider, KokoroProvider, OllamaTtsProbe, TtsProvider
from voice_platform import tts_pb2_grpc

settings = get_settings()
logger = logging.getLogger(__name__)


async def serve_grpc(provider: TtsProvider) -> None:
    server = grpc.aio.server()
    tts_pb2_grpc.add_TextToSpeechServicer_to_server(TextToSpeechService(provider), server)
    server.add_insecure_port("[::]:50054")
    await server.start()
    await server.wait_for_termination()


async def serve_http() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=8094, log_level=settings.log_level.lower())
    server = uvicorn.Server(config)
    await server.serve()


async def build_provider() -> TtsProvider:
    probe = OllamaTtsProbe(settings.ollama_base_url, settings.ollama_tts_model)
    if settings.tts_provider == "ollama":
        if await probe.is_usable():
            raise RuntimeError("Ollama TTS audio output is not implemented in this stack")
        logger.warning("Configured TTS provider 'ollama' is unusable; falling back to Kokoro")

    if settings.tts_provider in {"kokoro", "ollama"}:
        try:
            provider = KokoroProvider(
                settings.tts_voice,
                speed=settings.tts_speed,
                device=settings.tts_device,
                repo_id=settings.tts_kokoro_repo,
                lang_code=settings.tts_lang_code,
            )
            await provider.warmup()
            return provider
        except Exception as exc:
            logger.warning("Kokoro initialization failed; falling back to espeak-ng", extra={"error": str(exc)})

    return EspeakProvider(settings.tts_voice)


async def main() -> None:
    configure_logging(settings.log_level)
    configure_tracing("tts-service", settings.otel_exporter_otlp_endpoint)
    provider = await build_provider()
    await asyncio.gather(serve_http(), serve_grpc(provider))


if __name__ == "__main__":
    asyncio.run(main())
