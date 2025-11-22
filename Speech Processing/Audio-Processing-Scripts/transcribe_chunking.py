import os
import json
import time
import torch
import numpy as np
import soundfile as sf
from glob import glob

from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
)

# -----------------------------
# Paths (edit only if your layout changes)
# -----------------------------
RUN_ROOT = r"C:\Proxima Tech Solutions\Proxima AI Voice Call Center\Project-Code\Fine-Tuned-STT\Whisper-FT-V2"
CKPT_DIR = os.path.join(RUN_ROOT, "checkpoint-3672")  # change if you want another checkpoint

SEGMENTS_DIR = r"C:\Proxima Tech Solutions\Proxima AI Voice Call Center\Bakcell-Data-Prep\Bakcell-Channels"
OUTPUT_JSON = os.path.join(SEGMENTS_DIR, "transcriptions.json")

# -----------------------------
# Test mode
# -----------------------------
# Set to an integer (e.g., 10) to transcribe only the first N files.
# Set to None for full run.
TEST_FIRST_N = None  # e.g., 10 for a quick dry-run

# -----------------------------
# Chunking config (for long audios)
# -----------------------------
# Whisper is trained on ~30s segments; we keep a bit below that.
CHUNK_SECONDS = 25.0          # length of each chunk in seconds
CHUNK_OVERLAP_SECONDS = 5.0   # overlap between consecutive chunks in seconds

# -----------------------------
# Device / dtype
# -----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
use_bf16 = (device == "cuda") and torch.cuda.get_device_capability(0)[0] >= 8  # Hopper+
dtype = torch.bfloat16 if use_bf16 else (torch.float16 if device == "cuda" else torch.float32)

# -----------------------------
# Load model & processor
# -----------------------------
processor = WhisperProcessor.from_pretrained(RUN_ROOT)
model = WhisperForConditionalGeneration.from_pretrained(CKPT_DIR, torch_dtype=dtype).to(device)
model.eval()

# Ensure AZ transcription settings
model.generation_config.language = "az"
model.generation_config.task = "transcribe"
model.generation_config.forced_decoder_ids = None
model.generation_config.suppress_tokens = []

SR = 16000  # expected sample rate for the model
MAX_LEN = 448  # consistent with your training


def _to_float32(wav: np.ndarray) -> np.ndarray:
    """Cast to float32 in [-1, 1]."""
    if np.issubdtype(wav.dtype, np.integer):
        wav = wav.astype(np.float32) / np.iinfo(wav.dtype).max
    elif wav.dtype != np.float32:
        wav = wav.astype(np.float32)
    # Clamp just in case
    if wav.size:
        m = np.max(np.abs(wav))
        if m > 1.0:
            wav = wav / m
    return wav


def load_segment(path: str) -> np.ndarray:
    """
    Read mono WAV, return float32 mono at SR Hz.
    If your files are not at SR=16000, you should resample before or here.
    """
    wav, sr = sf.read(path, always_2d=False)
    if wav.ndim == 2:
        wav = wav.mean(axis=1)  # safety: downmix if not mono
    if sr != SR:
        raise ValueError(f"Expected {SR} Hz, got {sr} Hz for {os.path.basename(path)}")
    return _to_float32(wav)


@torch.inference_mode()
def transcribe_array(wav: np.ndarray) -> str:
    feats = processor.feature_extractor(wav, sampling_rate=SR, return_tensors="pt").input_features.to(device)
    if device == "cuda":
        with torch.autocast(device_type="cuda", dtype=dtype):
            out_ids = model.generate(inputs=feats, max_length=MAX_LEN, do_sample=False, num_beams=3)
    else:
        out_ids = model.generate(inputs=feats, max_length=MAX_LEN, do_sample=False, num_beams=3)
    return processor.tokenizer.batch_decode(out_ids, skip_special_tokens=True)[0]


def transcribe_long_audio(wav: np.ndarray) -> str:
    """
    Transcribe a potentially long waveform by chunking it into overlapping windows.
    Returns a single concatenated transcript string.
    """
    if wav.size == 0:
        return ""

    chunk_size = int(CHUNK_SECONDS * SR)
    overlap_size = int(CHUNK_OVERLAP_SECONDS * SR)
    # Step between chunk starts
    step = max(chunk_size - overlap_size, 1)

    texts = []
    n_samples = len(wav)
    start = 0
    chunk_idx = 0

    while start < n_samples:
        end = min(start + chunk_size, n_samples)
        chunk = wav[start:end]
        if chunk.size == 0:
            break

        text_chunk = transcribe_array(chunk)
        text_chunk = text_chunk.strip()
        if text_chunk:
            texts.append(text_chunk)

        chunk_idx += 1
        if end >= n_samples:
            break
        start += step

    # Simple concatenation; you could later add smarter merging if you want.
    return " ".join(texts)


def load_existing_results(json_path: str) -> dict:
    """
    Load existing transcription results from JSON file if it exists.
    Returns empty dict if file doesn't exist or can't be parsed.
    """
    if not os.path.exists(json_path):
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load existing results from {json_path}: {e}")
        print("Starting fresh transcription...")
        return {}


def save_results_incrementally(results: dict, json_path: str):
    """
    Save results to JSON file incrementally (after each transcription).
    """
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: Could not save results to {json_path}: {e}")


def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    wav_paths = sorted(glob(os.path.join(SEGMENTS_DIR, "*.wav")))
    if not wav_paths:
        print(f"No .wav files found in: {SEGMENTS_DIR}")
        return

    # Load existing results to resume from where we left off
    results = load_existing_results(OUTPUT_JSON)
    already_processed = set(results.keys())

    if already_processed:
        print(f"Found {len(already_processed)} already processed files. Resuming...")

    # Apply test-mode slicing
    if TEST_FIRST_N is None:
        chosen_paths = wav_paths
        test_info = "full run"
    else:
        n = max(0, int(TEST_FIRST_N))
        chosen_paths = wav_paths[:n]
        test_info = f"TEST MODE: first {len(chosen_paths)} file(s)"

    if not chosen_paths:
        print("Nothing to process (check TEST_FIRST_N or your folder).")
        return

    # Filter out already processed files
    paths_to_process = []
    for path in chosen_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        if name not in already_processed:
            paths_to_process.append(path)

    total_files = len(chosen_paths)
    already_done = len(chosen_paths) - len(paths_to_process)

    if not paths_to_process:
        print(f"All {total_files} files already transcribed. Nothing to do!")
        return

    t_start = time.time()
    print(f"Found {len(wav_paths)} files total; {test_info}.")
    print(f"Already transcribed: {already_done}/{total_files}")
    print(f"Remaining to process: {len(paths_to_process)}")
    print(f"Starting transcription on {device}…\n")

    for i, path in enumerate(paths_to_process, 1):
        name = os.path.splitext(os.path.basename(path))[0]  # segment name without extension
        try:
            t0 = time.time()
            wav = load_segment(path)
            # NEW: handle long audio with chunking
            text = transcribe_long_audio(wav)

            results[name] = text
            dt = time.time() - t0

            # Save after each successful transcription (incremental save)
            save_results_incrementally(results, OUTPUT_JSON)

            print(f"[{i}/{len(paths_to_process)}] {name}: {dt:.2f}s")
        except Exception as e:
            # Record error text to keep a single JSON output; adjust if you prefer to skip.
            err_msg = f"ERROR: {type(e).__name__}: {e}"
            results[name] = err_msg

            # Save even with errors
            save_results_incrementally(results, OUTPUT_JSON)

            print(f"[{i}/{len(paths_to_process)}] {name}: {err_msg}")

    print(f"\nDone in {time.time() - t_start:.2f}s")
    print(f"Total transcribed (including errors): {len(results)}/{total_files}")
    print(f"Final output: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
