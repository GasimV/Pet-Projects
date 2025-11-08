#!/usr/bin/env python3
# python test_fw.py /mnt/c/Users/ertan/OneDrive/Desktop/test.wav --lang az --temperature 0.1
# python test_fw.py /mnt/c/Users/ertan/OneDrive/Desktop/test4b.wav    --lang az   --temperature 0   --beam_size 5   --best_of 1   
import time, sys, argparse, wave, struct, re
from faster_whisper import WhisperModel
from ctranslate2 import get_cuda_device_count

def str2bool(x: str) -> bool:
    return x.lower() in ("1", "true", "t", "yes", "y", "on")

def make_silence_wav(path: str, dur_s: float = 0.3, sr: int = 16000):
    """Kısa bir sessiz WAV üret (warmup için)."""
    n = int(sr * dur_s)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        silence = struct.pack("<" + "h"*n, *([0]*n))
        w.writeframes(silence)

def trim_overlap(acc_text: str, new_text: str, tail: int = 80, min_match: int = 20) -> str:
    """acc_text kuyruğuyla new_text başı çakışırsa kırp."""
    if not acc_text or not new_text:
        return new_text
    tail_seg = acc_text[-tail:]
    k = min(len(tail_seg), len(new_text))
    cut = 0
    for i in range(k, min_match - 1, -1):
        if tail_seg.endswith(new_text[:i]):
            cut = i
            break
    return new_text[cut:] if cut > 0 else new_text

def unstutter(text: str) -> str:
    """Basit kekeleme temizleme: 'Higg higg' gibi tekrarları yumuşat."""
    s = re.sub(r'\b(\w{2,})\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    s = re.sub(r'(?:\b\w{2,}\b[ ,.;:!?-]+){1,3}\b(\w{2,})\b(?:[ ,.;:!?-]+\1\b){1,2}', r'\1', s, flags=re.IGNORECASE)
    return s

def main():
    ap = argparse.ArgumentParser(description="Faster-Whisper low-latency transcribe (no external VAD)")
    ap.add_argument("audio", help="Girdi ses dosyası")
    ap.add_argument("--lang", required=True, help="Dil kodu (ör. tr, en, de). AUTO kapalı.")
    ap.add_argument("--compute_type", default="float16",
                    choices=["float16", "int8_float16", "int8"],
                    help="Hız/VRAM (öneri: float16; sığmazsa int8_float16)")
    # Dahili VAD (opsiyonel)
    ap.add_argument("--vad", type=str2bool, default=False, help="Dahili VAD: true/false (vars: false)")
    ap.add_argument("--vad_min_sil_ms", type=int, default=150, help="VAD: min_silence_duration_ms")
    ap.add_argument("--vad_pad_ms", type=int, default=50, help="VAD: speech_pad_ms")

    # Arama / kalite
    ap.add_argument("--beam_size", type=int, default=1, help="Beam size (TTFT için 1 hızlı)")
    ap.add_argument("--best_of", type=int, default=1, help="best_of (greedy ise 1)")
    ap.add_argument("--temperature", type=float, default=0.2, help="0.0–0.3; tekrar azaltmada 0.2 iyi")

    # Bağlam ve zaman damgaları
    ap.add_argument("--condition_prev", action="store_true",
                    help="Önceki metne koşullansın (vars: kapalı)")
    ap.add_argument("--word_ts", action="store_true", help="Kelime zaman damgası AÇ (vars: kapalı)")
    ap.add_argument("--without_ts", type=str2bool, default=True,
                    help="Global timestamp KAPAT (vars: true → düşük TTFT)")
    ap.add_argument("--chunk_length", type=float, default=15.0,
                    help="Chunk süresi sn (küçük = daha düşük TTFT). Vars: 15.0")

    # Anti-repeat/uzunluk (opsiyonel, dikkatli)
    ap.add_argument("--repetition_penalty", type=float, default=1.0,
                    help=">1.0 tekrarları azaltır (örn 1.05). Aşırı kaçırma yapmayın.")
    ap.add_argument("--no_repeat_ngram_size", type=int, default=0,
                    help=">0 n-gram tekrarını yasaklar (örn 6). Çok yükseltmeyin.")
    ap.add_argument("--length_penalty", type=float, default=1.0,
                    help=">1.0 daha uzun, <1.0 daha kısa çıktılar.")
    ap.add_argument("--patience", type=float, default=1.0,
                    help="Beam aramada sabır (1.0 = kapalı).")

    # Post-process ve warmup
    ap.add_argument("--unstutter", type=str2bool, default=False,
                    help="Basit kekeleme temizleme uygula")
    ap.add_argument("--warmup", type=str2bool, default=True,
                    help="Ön ısıtma (sessiz 300ms) (vars: true)")
    args = ap.parse_args()

    # --- Model yükleme ---
    t0 = time.perf_counter()
    model = WhisperModel("/mnt/d/whisper-bizim-model-ct2", device="cuda", compute_type=args.compute_type)
    load_ms = int((time.perf_counter() - t0) * 1000)
    dev = "cuda" if get_cuda_device_count() > 0 else "cpu"
    print(f"[info] backend=CT2, device={dev}, compute_type={args.compute_type}, load_ms={load_ms}")

    # --- Warmup (opsiyonel) ---
    if args.warmup:
        _tmp = "_fw_warmup_silence.wav"
        make_silence_wav(_tmp, dur_s=0.3)
        _ = model.transcribe(
            _tmp,
            language=args.lang,
            vad_filter=False,
            beam_size=1, best_of=1, temperature=0.0,
            condition_on_previous_text=False,
            word_timestamps=False,
            without_timestamps=True,
        )

    # --- Transcribe ayarları ---
    transcribe_kwargs = dict(
        language=args.lang,
        beam_size=max(1, args.beam_size),
        best_of=max(1, args.best_of),
        temperature=float(args.temperature),
        condition_on_previous_text=bool(args.condition_prev),
        word_timestamps=bool(args.word_ts),
        without_timestamps=bool(args.without_ts),
        chunk_length=int(round(float(args.chunk_length))),  # güvenli cast
    )

    # İsteğe bağlı arama hiperparametreleri (yalnızca değişmişse ekle)
    if args.repetition_penalty and args.repetition_penalty != 1.0:
        transcribe_kwargs["repetition_penalty"] = float(args.repetition_penalty)
    if args.no_repeat_ngram_size and args.no_repeat_ngram_size > 0:
        transcribe_kwargs["no_repeat_ngram_size"] = int(args.no_repeat_ngram_size)
    if args.length_penalty and args.length_penalty != 1.0:
        transcribe_kwargs["length_penalty"] = float(args.length_penalty)
    if args.patience and args.patience != 1.0:
        transcribe_kwargs["patience"] = float(args.patience)

    # Dahili VAD
    if args.vad:
        transcribe_kwargs["vad_filter"] = True
        transcribe_kwargs["vad_parameters"] = {
            "min_silence_duration_ms": int(args.vad_min_sil_ms),
            "speech_pad_ms": int(args.vad_pad_ms),
        }
    else:
        transcribe_kwargs["vad_filter"] = False

    # --- Transcribe + TTFT ölçümü ---
    t1 = time.perf_counter()
    segments, info = model.transcribe(args.audio, **transcribe_kwargs)

    ttft_ms = None
    out_text = []
    for seg in segments:
        if ttft_ms is None:
            ttft_ms = int((time.perf_counter() - t1) * 1000)
        piece = seg.text
        if out_text:
            piece = trim_overlap("".join(out_text), piece)
        out_text.append(piece)

    total_ms = int((time.perf_counter() - t1) * 1000)
    final = "".join(out_text)
    if args.unstutter:
        final = unstutter(final)

    print(f"[timing] ttft_ms={ttft_ms}, total_ms={total_ms}, dur_s={getattr(info, 'duration', 0.0):.2f}")
    print("[text]", final)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
