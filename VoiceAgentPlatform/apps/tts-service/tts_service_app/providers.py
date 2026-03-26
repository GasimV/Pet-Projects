from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class AudioPacket:
    audio: bytes
    mime_type: str


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


class EspeakProvider:
    def __init__(self, voice: str) -> None:
        self._voice = voice

    async def synthesize(self, text: str) -> AudioPacket:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if executable is None:
            raise RuntimeError("espeak-ng or espeak must be installed for fallback TTS")
        process = await asyncio.create_subprocess_exec(
            executable,
            "-v",
            self._voice,
            "--stdout",
            text,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="ignore"))
        return AudioPacket(audio=stdout, mime_type="audio/wav")

