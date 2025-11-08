import os, sys, json, time, math, random, mimetypes, pathlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import soundfile as sf
import librosa
import requests
from tqdm import tqdm

from dotenv import load_dotenv
dotenv_path = r'C:\Proxima Tech Solutions\Proxima AI Voice Call Center\Project-Code\.env'
load_dotenv(dotenv_path=dotenv_path)

# -------------------------
# CONFIG (EDIT THESE)
# -------------------------
INPUT_ROOT  = r"C:\Proxima Tech Solutions\ASAN-Çağrı\Test"
OUTPUT_ROOT = r"C:\Proxima Tech Solutions\ASAN-Çağrı\Test\Test-Dataset"

# Azure OpenAI (Audio Transcriptions) — your deployment + endpoint
DEPLOYMENT = "gpt-4o-transcribe"
ENDPOINT   = (
    "https://ertan-mg91093j-eastus2.cognitiveservices.azure.com/"
    f"openai/deployments/{DEPLOYMENT}/audio/transcriptions?api-version=2024-10-21"
)
API_KEY    = os.getenv("AZURE_API_KEY")  # set in your env or System Properties

# Concurrency: start modest to avoid 429s; raise if your quota allows
MAX_WORKERS = 6

# Segmentation
TARGET_SEC   = 24.0         # aim per training example
OVERLAP_SEC  = 5            # add overlap so nothing is cut mid-phrase
MIN_KEEP_SEC = 1.0          # drop super-short fragments
SR           = 16000        # we’ll save 16 kHz mono for Whisper fine-tune
AUDIO_EXTS   = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm")

# Retry/backoff
MAX_RETRIES   = 6
TIMEOUT_SEC   = 300
BASE_PAUSE    = 0.15        # tiny sleep between successful calls

# -------------------------
# Optional: WebRTC VAD
# -------------------------
try:
    import webrtcvad
    _HAS_VAD = True
    vad = webrtcvad.Vad(1)  # 0–3; 2 is a good middle ground
    print("[INFO] WebRTC VAD available — using it for segmentation.")
except Exception:
    _HAS_VAD = False
    vad = None
    print("[INFO] WebRTC VAD not available (pip install webrtcvad) — falling back to energy-based VAD.")


def list_audio_files(root: str) -> List[str]:
    out = []
    for dirpath, _, files in os.walk(root):
        for n in files:
            if n.lower().endswith(AUDIO_EXTS):
                out.append(os.path.join(dirpath, n))
    return out


def load_resample_mono(path: str, sr: int = SR) -> np.ndarray:
    # librosa handles mp3/etc.; returns float32 in [-1, 1]
    wav, _ = librosa.load(path, sr=sr, mono=True)
    if wav.size == 0:
        return wav.astype(np.float32)
    # clamp if crazy peaks
    m = np.max(np.abs(wav))
    if m > 1.0:
        wav = wav / m
    return wav.astype(np.float32)


def _vad_segments_webrtc(wav: np.ndarray, sr: int = SR) -> List[Tuple[int, int]]:
    # WebRTC needs 10/20/30 ms frames @ 16k, 16-bit PCM
    int16 = np.clip(wav * 32768.0, -32768, 32767).astype(np.int16)
    frame_len = int(0.02 * sr)  # 20 ms
    bytes_per = frame_len * 2   # int16 => 2 bytes
    raw = int16.tobytes()

    flags = []
    for i in range(0, len(raw), bytes_per):
        frame = raw[i:i + bytes_per]
        if len(frame) < bytes_per:
            break
        flags.append(vad.is_speech(frame, sr))

    # merge frames to segments; smooth small gaps
    segs = []
    in_seg = False
    start = 0
    ms_per = 20.0
    for idx, speech in enumerate(flags):
        if speech and not in_seg:
            in_seg = True
            start = idx
        elif not speech and in_seg:
            in_seg = False
            end = idx
            segs.append((start, end))
    if in_seg:
        segs.append((start, len(flags)))

    # expand by 1 frame on each side (40 ms pad)
    expanded = []
    for s, e in segs:
        s = max(0, s - 1)
        e = min(len(flags), e + 1)
        expanded.append((s, e))

    # frames -> samples
    spans = []
    for s, e in expanded:
        ss = int(s * ms_per / 1000.0 * sr)
        ee = int(e * ms_per / 1000.0 * sr)
        if (ee - ss) / sr >= MIN_KEEP_SEC:
            spans.append((ss, ee))
    return spans


def _vad_segments_energy(wav: np.ndarray, sr: int = SR) -> List[Tuple[int, int]]:
    # Simple energy gate fallback
    hop = int(0.02 * sr)  # 20 ms
    win = int(0.05 * sr)  # 50 ms
    if len(wav) < win:
        return []
    frames = librosa.util.frame(wav, frame_length=win, hop_length=hop).T
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    thr = max(1e-6, np.median(rms) * 0.6)  # adaptive threshold
    speech = rms > thr

    segs = []
    in_seg = False
    for i, v in enumerate(speech):
        if v and not in_seg:
            in_seg = True
            start = i
        elif not v and in_seg:
            in_seg = False
            end = i
            segs.append((start, end))
    if in_seg:
        segs.append((start, len(speech)))

    # join near gaps < 200 ms
    spans = []
    def f2s(fr): return int(fr * hop)
    last = None
    for s, e in segs:
        s_s, e_s = f2s(s), f2s(e)
        if last is None:
            last = [s_s, e_s]
        else:
            if s_s - last[1] < int(0.2 * sr):
                last[1] = e_s
            else:
                spans.append(tuple(last))
                last = [s_s, e_s]
    if last is not None:
        spans.append(tuple(last))

    spans = [(s, e) for (s, e) in spans if (e - s) / sr >= MIN_KEEP_SEC]
    return spans


def vad_segments(wav: np.ndarray, sr: int = SR) -> List[Tuple[int, int]]:
    if _HAS_VAD:
        return _vad_segments_webrtc(wav, sr)
    return _vad_segments_energy(wav, sr)


def pack_into_windows(spans: List[Tuple[int, int]],
                      sr: int = SR,
                      target: float = TARGET_SEC,
                      overlap: float = OVERLAP_SEC) -> List[Tuple[int, int]]:
    """
    Take VAD spans (sample start/end) and accumulate into ~target-second windows,
    snapping cuts to VAD boundaries when possible. Adds 'overlap' at joins.
    """
    target_samps = int(target * sr)
    overlap_samps = int(overlap * sr)
    out = []
    cur_s = None
    cur_e = None

    def flush():
        nonlocal cur_s, cur_e
        if cur_s is not None and cur_e is not None:
            out.append((cur_s, cur_e))
        cur_s = cur_e = None

    for s, e in spans:
        if cur_s is None:
            cur_s, cur_e = s, e
            continue
        # If adding this span stays within target-ish, extend
        if (e - cur_s) <= target_samps:
            cur_e = e
            continue
        # Otherwise, close current window at previous VAD end
        flush()
        # Next window begins slightly before this VAD start (overlap)
        cur_s = max(0, s - overlap_samps)
        cur_e = e

    flush()

    # Ensure each is at least MIN_KEEP_SEC
    out = [(s, e) for (s, e) in out if (e - s) / sr >= MIN_KEEP_SEC]
    return out


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def azure_transcribe(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    for attempt in range(MAX_RETRIES):
        try:
            with open(path, "rb") as f:
                files = {"file": (os.path.basename(path), f, mime)}
                data = {"model": DEPLOYMENT}  # deployment is also in the URL; harmless to send
                headers = {"api-key": API_KEY}
                r = requests.post(ENDPOINT, headers=headers, files=files, data=data, timeout=TIMEOUT_SEC)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep((2 ** attempt) + random.random())
                continue
            r.raise_for_status()
            try:
                j = r.json()
                txt = j.get("text")
                return txt if txt is not None else r.text
            except ValueError:
                return r.text
        except requests.RequestException:
            if attempt < MAX_RETRIES - 1:
                time.sleep((2 ** attempt) + random.random())
                continue
            raise
    raise RuntimeError("Azure transcription exhausted retries")


@dataclass
class Job:
    in_path: str
    out_wav: str
    out_txt: str


def build_jobs_for_file(src_path: str) -> List[Job]:
    wav = load_resample_mono(src_path, SR)
    if wav.size == 0:
        return []

    spans = vad_segments(wav, SR)
    if not spans:
        # fall back: fixed windows with overlap if VAD failed
        step = int((TARGET_SEC - OVERLAP_SEC) * SR)
        chunk = int(TARGET_SEC * SR)
        spans = []
        i = 0
        N = len(wav)
        while i < N:
            s = i
            e = min(i + chunk, N)
            spans.append((s, e))
            if e == N:
                break
            i += step

    windows = pack_into_windows(spans, SR, TARGET_SEC, OVERLAP_SEC)

    jobs: List[Job] = []
    base = Path(src_path).stem
    # keep directory structure info in the filename to avoid collisions
    rel = Path(src_path).relative_to(INPUT_ROOT)
    rel_slug = "_".join(rel.parts[:-1] + (base,))
    rel_slug = "".join(c if c.isalnum() or c in "._-" else "_" for c in rel_slug)[:160]

    for idx, (s, e) in enumerate(windows):
        seg = wav[s:e]
        if (e - s) / SR < MIN_KEEP_SEC:
            continue
        out_wav = Path(OUTPUT_ROOT) / f"{rel_slug}__seg{idx:04d}.wav"
        out_txt = str(out_wav) + ".txt"
        # write wav now (resume-safe for text) — 16-bit PCM
        sf.write(str(out_wav), seg, SR, subtype="PCM_16")
        jobs.append(Job(src_path, str(out_wav), out_txt))
    return jobs


def worker(job: Job):
    # Skip if transcript already exists and non-empty
    if os.path.exists(job.out_txt) and os.path.getsize(job.out_txt) > 0:
        return ("skip", job.out_txt)

    text = azure_transcribe(job.out_wav)
    payload = {"text": (text or "").strip(), "audio_path": job.out_wav}
    with open(job.out_txt, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        f.write("\n")

    time.sleep(BASE_PAUSE)
    return ("ok", job.out_txt)


def main():
    if not API_KEY:
        print("ERROR: Set AZURE_API_KEY in your environment.", file=sys.stderr)
        sys.exit(1)

    ensure_dir(Path(OUTPUT_ROOT))

    files = list_audio_files(INPUT_ROOT)
    if not files:
        print("No audio files found.")
        return

    # Build segmentation/transcription jobs
    all_jobs: List[Job] = []
    for p in tqdm(files, desc="Scanning & segmenting"):
        try:
            all_jobs.extend(build_jobs_for_file(p))
        except Exception as e:
            print(f"[seg-fail] {p} -> {e}", file=sys.stderr)

    print(f"Prepared {len(all_jobs)} segment(s) from {len(files)} file(s).")

    ok = skip = fail = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(worker, j) for j in all_jobs]
        for f in tqdm(as_completed(futs), total=len(futs), desc="Transcribing"):
            try:
                status, path = f.result()
                if status == "ok":
                    ok += 1
                elif status == "skip":
                    skip += 1
            except Exception as e:
                fail += 1
                print(f"[fail] {e}", file=sys.stderr)

    print(f"\nDone. ok={ok} skip={skip} fail={fail}  => Output dir: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
