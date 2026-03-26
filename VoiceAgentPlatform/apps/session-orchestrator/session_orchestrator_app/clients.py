from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import grpc

from voice_platform import llm_pb2, llm_pb2_grpc, rag_pb2, rag_pb2_grpc, stt_pb2, stt_pb2_grpc, tool_pb2, tool_pb2_grpc, tts_pb2, tts_pb2_grpc


class ServiceClients:
    def __init__(self) -> None:
        self._stt_channel = grpc.aio.insecure_channel(os.getenv("STT_GRPC_TARGET", "stt-service:50052"))
        self._llm_channel = grpc.aio.insecure_channel(os.getenv("LLM_GRPC_TARGET", "llm-service:50053"))
        self._tts_channel = grpc.aio.insecure_channel(os.getenv("TTS_GRPC_TARGET", "tts-service:50054"))
        self._tool_channel = grpc.aio.insecure_channel(os.getenv("TOOL_GRPC_TARGET", "tool-service:50055"))
        self._rag_channel = grpc.aio.insecure_channel(os.getenv("RAG_GRPC_TARGET", "rag-service:50056"))
        self.stt = stt_pb2_grpc.SpeechToTextStub(self._stt_channel)
        self.llm = llm_pb2_grpc.LanguageModelStub(self._llm_channel)
        self.tts = tts_pb2_grpc.TextToSpeechStub(self._tts_channel)
        self.tool = tool_pb2_grpc.ToolRuntimeStub(self._tool_channel)
        self.rag = rag_pb2_grpc.RetrievalAugmentationStub(self._rag_channel)

    async def transcribe(self, meta, pcm: bytes, sample_rate: int, is_final: bool) -> tuple[str, float]:
        async def iterator():
            yield stt_pb2.SttAudioChunk(
                meta=meta,
                pcm=pcm,
                sample_rate=sample_rate,
                end_of_turn=is_final,
            )

        async for reply in self.stt.StreamTranscribe(iterator()):
            return reply.text, reply.confidence
        return "", 0.0

    async def retrieve(self, meta, query: str, top_k: int = 3):
        return await self.rag.Retrieve(rag_pb2.RagRequest(meta=meta, query=query, top_k=top_k))

    async def execute_tool(self, meta, name: str, arguments_json: str) -> dict:
        reply = await self.tool.Execute(
            tool_pb2.ToolRequest(meta=meta, name=name, arguments_json=arguments_json)
        )
        return json.loads(reply.output_json)

    async def synthesize(self, meta, text: str, voice: str) -> bytes:
        async for reply in self.tts.Synthesize(
            tts_pb2.SynthesisRequest(meta=meta, text=text, voice=voice, flush=True)
        ):
            return reply.audio
        return b""

    async def stream_generate(
        self,
        meta,
        messages: list[dict[str, str]],
        system_prompt: str,
        context: str,
        enable_tools: bool,
    ) -> AsyncIterator[llm_pb2.GenerateChunk]:
        request = llm_pb2.GenerateRequest(
            meta=meta,
            messages=[llm_pb2.ChatMessage(**message) for message in messages],
            system_prompt=system_prompt,
            context=context,
            enable_tools=enable_tools,
        )
        async for chunk in self.llm.StreamGenerate(request):
            yield chunk

