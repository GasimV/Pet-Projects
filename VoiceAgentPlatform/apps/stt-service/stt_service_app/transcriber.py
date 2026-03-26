from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except Exception:  # pragma: no cover
    WhisperModel = None


@dataclass(slots=True)
class TranscriptResult:
    text: str
    confidence: float


class FasterWhisperTranscriber:
    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _ensure_model(self):
        if self._model is None and WhisperModel is not None:
            self._model = WhisperModel(self._model_name, device=self._device, compute_type=self._compute_type)
        return self._model

    @staticmethod
    def _pcm_to_float32(raw_audio: bytes) -> np.ndarray:
        audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

    def transcribe(self, raw_audio: bytes, sample_rate: int = 16000) -> TranscriptResult:
        if not raw_audio:
            return TranscriptResult(text="", confidence=0.0)

        model = self._ensure_model()
        if model is None:
            return TranscriptResult(text="mock transcript", confidence=0.5)

        audio = self._pcm_to_float32(raw_audio)
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format="WAV")
        buffer.seek(0)

        segments, info = model.transcribe(
            buffer,
            language="en",
            vad_filter=False,
            beam_size=1,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        confidence = 1.0 - float(getattr(info, "language_probability", 0.5))
        return TranscriptResult(text=text, confidence=max(0.1, confidence))

