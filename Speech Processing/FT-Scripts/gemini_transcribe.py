#!/usr/bin/env python3
"""
gemini_transcribe.py
- Tek ya da birden fazla ses dosyasını Gemini 2.5 Pro ile transcribe eder.
- Çıktıyı aynı klasöre, aynı dosya adıyla .txt olarak yazar.
- Kullanım:
    python gemini_transcribe.py /path/a.wav /path/b.mp3
Önkoşul:
    pip install google-genai
Ortam:
    export GEMINI_API_KEY="YOUR_API_KEY"

Çalıştırma örnekleri:
    python3 gemini_transcribe.py "/mnt/c/Users/ertan/OneDrive/Desktop/asanhizmet/1738558802.3056950__seg0000.wav"
    python3 gemini_transcribe.py "file1.wav"
    python3 gemini_transcribe.py dir/*.wav # " işareti yokda glob
    okuduysan sağol

"""

import os
import sys
import argparse
import mimetypes
from pathlib import Path
import glob
import time
from typing import List, Optional

from google import genai
from google.genai import types

from dotenv import load_dotenv
dotenv_path = '/mnt/ebs_volume/.env'
load_dotenv(dotenv_path=dotenv_path)

PROMPT_TRANSCRIBE = """Task: Transcribe EVERYTHING spoken exactly as-is (no omissions, no summaries).

Rules:
- Language: auto-detect;
- Output: plain text only in one line.
- Keep natural spelling/numbers; preserve abbreviations (e.g., "AQTA", "ASAN").
- Mark noise/unintelligible as "[noise]" (no guesses).
- Preserve code-switching (mixed TR/AZ/EN/RU).
- Conference/Phone: do not write turn-by-turn, plain append.
"""

MODEL_ID = "gemini-2.5-pro"  # GA model id

SUPPORTED_MIME = {
    "audio/x-aac",
    "audio/flac",
    "audio/mp3",
    "audio/m4a",
    "audio/mpeg",
    "audio/mpga",
    "audio/mp4",
    "audio/ogg",
    "audio/pcm",
    "audio/wav",
    "audio/webm",
}

def guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    # Bazı .wav/.mp3 ortamlarında None döner; güvenli varsayımlar:
    if mt is None:
        if path.suffix.lower() == ".wav":
            mt = "audio/wav"
        elif path.suffix.lower() in (".mp3",):
            mt = "audio/mp3"
        else:
            mt = "application/octet-stream"
    return mt

def ensure_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        sys.exit("Hata: GEMINI_API_KEY ortam değişkenini ayarla.")
    return key


def transcribe_file(client: genai.Client, audio_path: Path) -> str:
    if not audio_path.exists():
        raise FileNotFoundError(f"Bulunamadı: {audio_path}")

    mime = guess_mime(audio_path)

    # ✅ Single API call: send bytes inline
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            PROMPT_TRANSCRIBE,
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
        ],
        # Optional caps for very long outputs (tune if you see truncation) #max_output_tokens=2048
        config=types.GenerateContentConfig(temperature=0), # config=types.GenerateContentConfig(temperature=0, max_output_tokens=2048)
    )
    return resp.text or ""


def write_sibling_txt(audio_path: Path, text: str) -> Path:
    out_path = audio_path.with_suffix(".txt")
    out_path.write_text(text, encoding="utf-8")
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gemini 2.5 Pro STT (tek/çoklu dosya)")
    parser.add_argument("inputs", nargs="+", help="Ses dosyası yol(ları)")
    parser.add_argument("--max-files", type=int, default=None,
                        help="Günde işlenecek maksimum dosya sayısı (rate limit için).")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="Her dosya arası bekleme süresi (saniye).")
    args = parser.parse_args(argv)

    ensure_api_key()
    client = genai.Client()

    # 🔧 Expand wildcards manually (Windows fix)
    all_files = []
    for p in args.inputs:
        expanded = glob.glob(p)
        all_files.extend(expanded or [p])
    all_files = [Path(f) for f in all_files]

    # Limit for daily safe quota
    if args.max_files is not None:
        all_files = all_files[:args.max_files]

    total = 0
    for audio in all_files:
        out_txt = audio.with_suffix(".txt")
        if out_txt.exists() and out_txt.stat().st_size > 0:
            print(f"[SKIP] {out_txt} already exists.")
            continue

        print(f"[INFO] Transcribing: {audio}")
        try:
            text = transcribe_file(client, audio)
            outp = write_sibling_txt(audio, text)
            print(f"[OK] Saved: {outp}")
            total += 1
        except Exception as e:
            print(f"[ERR] {audio}: {e}")
        finally:
            time.sleep(args.sleep)

    print(f"[DONE] {total}/{len(all_files)} yeni dosya işlendi.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
