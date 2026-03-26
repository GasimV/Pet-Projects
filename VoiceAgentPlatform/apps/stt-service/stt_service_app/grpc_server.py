from __future__ import annotations

import grpc

from stt_service_app.transcriber import FasterWhisperTranscriber
from voice_platform import common_pb2, stt_pb2, stt_pb2_grpc


class SpeechToTextService(stt_pb2_grpc.SpeechToTextServicer):
    def __init__(self, transcriber: FasterWhisperTranscriber) -> None:
        self._transcriber = transcriber

    async def StreamTranscribe(self, request_iterator, context: grpc.aio.ServicerContext):
        chunks: list[bytes] = []
        sample_rate = 16000
        meta = None
        is_final = False
        async for request in request_iterator:
            meta = request.meta
            sample_rate = request.sample_rate or sample_rate
            chunks.append(request.pcm)
            is_final = request.end_of_turn
        result = self._transcriber.transcribe(b"".join(chunks), sample_rate=sample_rate)
        yield stt_pb2.TranscriptChunk(
            meta=meta,
            text=result.text,
            is_final=is_final,
            confidence=result.confidence,
        )

    async def Health(self, request: common_pb2.Empty, context: grpc.aio.ServicerContext):
        return common_pb2.HealthReply(status="ok")

