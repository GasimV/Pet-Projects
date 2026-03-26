from __future__ import annotations

import asyncio
import io
import shutil
from dataclasses import dataclass
from typing import Protocol

import httpx
import numpy as np
import soundfile as sf

try:
    from kokoro import KPipeline
except ImportError:  # pragma: no cover - exercised in container/runtime
    KPipeline = None


@dataclass(slots=True)
class AudioPacket:
    audio: bytes
    mime_type: str


class TtsProvider(Protocol):
    async def synthesize(self, text: str, voice: str | None = None) -> AudioPacket: ...


class OllamaTtsProbe:
    def __init__(self, base_url: str, requested_model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._requested_model = requested_model

    async def is_usable(self) -> bool:
        if not self._requested_model:
            return False
        async with httpx.AsyncClient(base_url=self._base_url, timeout=5.0) as client:
            try:
                response = await client.get("/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                present = any(model.get("name") == self._requested_model for model in models)
                return present and False
            except Exception:
                return False


class KokoroProvider:
    SAMPLE_RATE = 24000
    DEFAULT_REPO = "hexgrad/Kokoro-82M"
    DEFAULT_LANG_CODE = "a"
    DEFAULT_VOICE = "af_heart"

    def __init__(
        self,
        voice: str,
        *,
        speed: float = 1.0,
        device: str = "cpu",
        repo_id: str = DEFAULT_REPO,
        lang_code: str = DEFAULT_LANG_CODE,
    ) -> None:
        if KPipeline is None:
            raise RuntimeError("kokoro must be installed to use the Kokoro TTS provider")
        self._default_voice = voice or self.DEFAULT_VOICE
        self._speed = speed
        self._device = device or "cpu"
        self._repo_id = repo_id or self.DEFAULT_REPO
        self._lang_code = lang_code or self.DEFAULT_LANG_CODE
        self._pipeline = None
        self._init_lock = asyncio.Lock()

    async def warmup(self) -> None:
        await self._ensure_pipeline()
        await asyncio.to_thread(self._pipeline.load_voice, self._normalize_voice(None))

    async def synthesize(self, text: str, voice: str | None = None) -> AudioPacket:
        await self._ensure_pipeline()
        return await asyncio.to_thread(self._synthesize_sync, text, self._normalize_voice(voice))

    async def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return
        async with self._init_lock:
            if self._pipeline is None:
                self._pipeline = await asyncio.to_thread(
                    lambda: KPipeline(
                        lang_code=self._lang_code,
                        repo_id=self._repo_id,
                        device=self._device,
                    )
                )

    def _normalize_voice(self, voice: str | None) -> str:
        requested = (voice or "").strip().lower()
        if not requested or requested in {"en", "en-us", "en_us", "default"}:
            return self._default_voice
        return voice or self._default_voice

    def _synthesize_sync(self, text: str, voice: str) -> AudioPacket:
        segments = []
        for result in self._pipeline(text, voice=voice, speed=self._speed, split_pattern=None):
            if result.audio is None:
                continue
            audio = result.audio.detach().cpu().numpy().astype(np.float32)
            segments.append(audio)
        if not segments:
            raise RuntimeError("Kokoro produced no audio")
        waveform = np.concatenate(segments)
        buffer = io.BytesIO()
        sf.write(buffer, waveform, self.SAMPLE_RATE, format="WAV")
        return AudioPacket(audio=buffer.getvalue(), mime_type="audio/wav")


class EspeakProvider:
    def __init__(self, voice: str) -> None:
        self._voice = voice

    async def synthesize(self, text: str, voice: str | None = None) -> AudioPacket:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if executable is None:
            raise RuntimeError("espeak-ng or espeak must be installed for fallback TTS")
        process = await asyncio.create_subprocess_exec(
            executable,
            "-v",
            voice or self._voice,
            "--stdout",
            text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="ignore"))
        return AudioPacket(audio=stdout, mime_type="audio/wav")
