# segmentation_only.py
import os
from pathlib import Path
from typing import List, Tuple
import numpy as np
import soundfile as sf
import librosa

# -------- Paths (edit if needed) --------
INPUT_ROOT  = "/mnt/ebs_volume/2025/"
OUTPUT_ROOT = "/mnt/ebs_volume/ASAN-CALL-CENTER-DATASET/"

# -------- Audio / segmentation params --------
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm")
SR = 16000
CHUNK_SEC = 24.0
OVERLAP_SEC = 2.0
MIN_KEEP_SEC = 1.0   # drop tiny tail pieces

# -------- Test mode: only first N source files; set None for full run --------
TEST_FIRST_N = None

def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)

def list_input_files(root: str) -> List[str]:
    files = []
    for dp, _, fnames in os.walk(root):
        for n in fnames:
            if n.lower().endswith(AUDIO_EXTS):
                files.append(os.path.join(dp, n))
    files.sort()
    return files

def load_resample_mono(path: str, sr: int = SR) -> np.ndarray:
    wav, _ = librosa.load(path, sr=sr, mono=True)  # float32 [-1,1]
    if wav.size:
        mx = float(np.max(np.abs(wav)))
        if mx > 1.0:
            wav = wav / mx
    return wav.astype(np.float32)

def fixed_windows(n_samps: int, sr: int = SR, chunk_sec: float = CHUNK_SEC, overlap_sec: float = OVERLAP_SEC):
    chunk = int(chunk_sec * sr)
    step  = int((chunk_sec - overlap_sec) * sr)
    spans = []
    i = 0
    while i < n_samps:
        s = i
        e = min(i + chunk, n_samps)
        spans.append((s, e))
        if e == n_samps:
            break
        i += step
    # drop very small fragments
    spans = [(s, e) for (s, e) in spans if (e - s)/sr >= MIN_KEEP_SEC]
    return spans

def write_segments_for_file(src_path: str) -> int:
    wav = load_resample_mono(src_path, SR)
    if wav.size == 0:
        return 0

    rel = Path(src_path).relative_to(INPUT_ROOT)
    out_dir = Path(OUTPUT_ROOT) / rel.parent
    ensure_dir(out_dir)

    base = Path(src_path).stem
    spans = fixed_windows(len(wav), SR, CHUNK_SEC, OVERLAP_SEC)

    made = 0
    for idx, (s, e) in enumerate(spans):
        seg = wav[s:e]
        out_wav = out_dir / f"{base}__seg{idx:04d}.wav"
        if not out_wav.exists():
            sf.write(str(out_wav), seg, SR, subtype="PCM_16")
            made += 1
    return made

def main():
    ensure_dir(OUTPUT_ROOT)
    src_files = list_input_files(INPUT_ROOT)
    if TEST_FIRST_N is not None:
        src_files = src_files[:TEST_FIRST_N]
    print(f"Found {len(src_files)} source file(s). Starting segmentation...")

    total_segments = 0
    for i, p in enumerate(src_files, 1):
        made = write_segments_for_file(p)
        total_segments += made
        if i % 5 == 0:
            print(f"[{i}/{len(src_files)}] last={made} new segments, total={total_segments}")

    print(f"\nSegmentation complete. New segments written: {total_segments}")
    print(f"Output root: {OUTPUT_ROOT}")

if __name__ == "__main__":
    main()
