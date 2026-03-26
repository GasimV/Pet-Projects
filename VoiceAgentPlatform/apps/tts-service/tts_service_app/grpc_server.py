from __future__ import annotations

import grpc

from tts_service_app.providers import EspeakProvider
from voice_platform import common_pb2, tts_pb2, tts_pb2_grpc


class TextToSpeechService(tts_pb2_grpc.TextToSpeechServicer):
    def __init__(self, provider: EspeakProvider) -> None:
        self._provider = provider

    async def Synthesize(
        self, request: tts_pb2.SynthesisRequest, context: grpc.aio.ServicerContext
    ):
        packet = await self._provider.synthesize(request.text)
        yield tts_pb2.SynthesisChunk(
            meta=request.meta,
            audio=packet.audio,
            mime_type=packet.mime_type,
            is_final=True,
        )

    async def Health(self, request: common_pb2.Empty, context: grpc.aio.ServicerContext):
        return common_pb2.HealthReply(status="ok")

