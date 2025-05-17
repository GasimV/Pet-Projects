import os
import base64
import tempfile

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# ==== Load your STT (Whisper) ====
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline
from pathlib import Path
from django.conf import settings

# Path to your model files (change if your folder name differs)
MODEL_DIR = os.path.join(settings.BASE_DIR, "asan_speech", "models", "whisper-az-small-finetuned", "checkpoint-210")
PICKLE_PATH = os.path.join(settings.BASE_DIR, "asan_speech", "models", "all_segments.pkl")
PROCESSOR_DIR = os.path.join(settings.BASE_DIR, "asan_speech", "models", "whisper-az-small-finetuned")

asr_model = WhisperForConditionalGeneration.from_pretrained(MODEL_DIR)
asr_processor = WhisperProcessor.from_pretrained(PROCESSOR_DIR)

asr_model.generation_config.language = "az"
asr_model.config.forced_decoder_ids = asr_processor.get_decoder_prompt_ids(
    language="azerbaijani", task="transcribe"
)
asr_pipe = pipeline(
    "automatic-speech-recognition",
    model=asr_model,
    tokenizer=asr_processor.tokenizer,
    feature_extractor=asr_processor.feature_extractor,
)

# ==== Load your TTS (VITS) ====
from transformers import VitsModel, AutoTokenizer
import torch

tts_model = VitsModel.from_pretrained("BHOSAI/SARA_TTS")
tts_tokenizer = AutoTokenizer.from_pretrained("BHOSAI/SARA_TTS")


def index(request):
    return render(request, "asan_speech/index.html")


@csrf_exempt
def process_audio(request):
    """
    Receives a POST with 'audio' file (webm), runs ASR → dummy QA → TTS.
    Returns JSON: { transcript: str, tts_audio: base64-wav }
    """
    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "No audio uploaded"}, status=400)

    # save to temp file
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tf:
        for chunk in audio_file.chunks():
            tf.write(chunk)
        tmp_path = tf.name

    # 1) ASR
    asr_out = asr_pipe(tmp_path)
    transcript = asr_out.get("text", "").strip()
    os.unlink(tmp_path)

    # 2) Dummy backend logic
    if (
            "Doğumun qeydə alınmasının rüsumu nədir" in transcript
            or "Doğumun qeyd alınmasının rüsumu nədir" in transcript
            or "Doğum rüsumu" in transcript
    ):
        answer_text = (
            "Doğumun qeydə alınması və bu barədə ilkin şəhadətnamələrin verilməsi "
            "üçün dövlət rüsumu ödənilmir."
        )
    else:
        answer_text = "Bağışlayın, bu sual üçün cavabım yoxdur."

    # 3) TTS: synthesize WAV
    tts_inputs = tts_tokenizer(answer_text, return_tensors="pt")
    with torch.no_grad():
        wav = tts_model(**tts_inputs).waveform  # shape [1, T]
    wav_np = wav.cpu().numpy()[0]

    # encode as WAV in memory
    import io, scipy.io.wavfile
    buffer = io.BytesIO()
    scipy.io.wavfile.write(buffer, tts_model.config.sampling_rate, wav_np)
    wav_bytes = buffer.getvalue()
    b64_wav = base64.b64encode(wav_bytes).decode("utf-8")

    return JsonResponse({
        "transcript": transcript,
        "answer": answer_text,
        "tts_audio": b64_wav,
    })
