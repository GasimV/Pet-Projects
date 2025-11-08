#!/usr/bin/env python3
"""
gemini_transcribe_batch.py
- Tek/çoklu ses dosyasını Gemini 2.5 Pro ile transcribe eder.
- Normal mod: her dosyaya ayrı senkron istek.
- Batch mod (--use-batch): klasördeki dosyaları 'batch-size' adetlik job'lar halinde kuyruğa atar,
  job bitince çıktıları aynı klasöre aynı ad + .txt yazar.
- İlerleme dosyası ile (checkpoint) kaldığı yerden devam eder; hata olursa hemen durur.
- PENDING takibi ve sonradan sonuç çekme (--check-pendings) desteklenir.

Kullanım örnekleri:
  # Normal (tek tek):
  python3 gemini_transcribe_batch.py /path/a.wav /path/b.mp3

  # Batch (klasör):
  python3 gemini_transcribe_batch.py --use-batch --dir /data/calls --batch-size 10000 --max-wait 10
  
  "--max-wait" batch i create ettikten sonra bekleme süresi
  "--batch-size"da sınır yok ama 1k 5k gibi test edip sorun yoksa 50k 100k basılabilir - ASIL SINIR DOSYA BOYUTU toplam batchler audiolar 2gb ı geçemez! 

  AI Studio (Gemini Developer API) Batch: JSONL satır sayısı için resmi “N adet” sınır yok. Pratik sınırlar dosya boyutu (2 GB) ve enqueue edebileceğin token limiti; ayrıca eşzamanlı batch sayısı (100) gibi rate-limitler var. Yani 10k–50k satır da olabilir; 2 GB ve token kotalarını aşmadığın sürece kabul edilir.

  ÖNEMLİ!!!! Büyük iş kuyruğu varsa 72 saate kadar bekleyebilir, batch-size'ı çok ABARTMA!

  # Sadece bekleyen job'ları sorgula ve bitenlerin çıktılarını yaz:
  python3 gemini_transcribe_batch.py --check-pendings 

  ÖRNEK AKIŞ:
CREATE:
    [INFO] Progress file: gemini_transcribe_progress.txt (done=0, pending=0)
    [INFO] Pending files to submit now: 10
    [BATCH] Submit: transcribe_batch-000001 (size=10)
    [BATCH] created: batches/00e1wndo6gfpkn610vkoosbg7i3mpd6ybqqx  (items=10)
    [BATCH] state: JOB_STATE_PENDING 

CHECK: 
[CHECK] job: batches/00e1wndo6gfpkn610vkoosbg7i3mpd6ybqqx
[CHECK] state: JOB_STATE_PENDING
[CHECK] still pending: batches/00e1wndo6gfpkn610vkoosbg7i3mpd6ybqqx
[CHECK] finalized: 0

SUCCESS:
[CHECK] job: batches/l8yym3vyc7ewd69lu0oer9q0pl38lxjkxshi
[CHECK] state: JOB_STATE_SUCCEEDED
[OK] Saved (check): /mnt/c/Users/ertan/OneDrive/Desktop/asanhizmet/1738558802.3056950__seg0007.txt
[OK] Saved (check): /mnt/c/Users/ertan/OneDrive/Desktop/asanhizmet/1738558802.3056950__seg0008.txt
[OK] Saved (check): /mnt/c/Users/ertan/OneDrive/Desktop/asanhizmet/1738558803.3056951__seg0000.txt
[CHECK] finalized: 1

Önkoşul:
  pip install -U google-genai
Ortam:
  export GEMINI_API_KEY="YOUR_API_KEY"
"""

import os
import sys
import time
import json
import argparse
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Any, Dict, Iterable
import base64

from google import genai
from google.genai import types

# -----------------------
# Ayarlar
# -----------------------
POLL_TIMEOUT_S = 10  # varsayılan bekleme (s)
STATE_DIR = Path(".gemini_batch_state")  # job->path eşlemesi için küçük state dosyaları

DEFAULT_PROGRESS_FILE = "gemini_transcribe_progress.txt"
DEFAULT_PENDING_FILE  = "batch_pending_list.txt"
DEFAULT_SUCCESS_FILE  = "batch_success_list.txt"

PROMPT_TRANSCRIBE = """Task: Transcribe EVERYTHING spoken exactly as-is (no omissions, no summaries).

Rules:
- Language: auto-detect;
- Output: plain text only (one line per utterance if possible).
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
    "audio/opus",
    "audio/amr",
}

AUDIO_EXTS = {
    ".aac", ".flac", ".mp3", ".m4a", ".mpeg", ".mpga", ".mp4",
    ".ogg", ".pcm", ".wav", ".webm"
}

# -----------------------
# Yardımcılar
# -----------------------
# ---- Raw dump helpers ----
def _raw_dir() -> Path:
    d = STATE_DIR / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _job_id_safe(job_name: str) -> str:
    return job_name.replace("/", "_")

def _dump_raw_jsonl(job_name: str, responses: List[Dict[str, Any]]) -> Path:
    """Tüm ham response objelerini JSONL olarak kaydet."""
    out = _raw_dir() / f"{_job_id_safe(job_name)}.responses.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for obj in responses:
            try:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            except Exception:
                # En kötü str(obj)
                f.write(str(obj) + "\n")
    return out

def _preview(obj: Any, limit: int = 400) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    if len(s) > limit:
        return s[:limit] + " …"
    return s


def _collect_batch_responses(job: Any, client: genai.Client) -> List[Dict[str, Any]]:
    """
    Batch job çıktısını farklı şemalardan okuyup bir response listesi döndürür.
    Önce dest.inlined_responses → sonra dest.file_name (Files API JSONL) → 
    eski şema: output.inlined_responses / output.files → en son GCS uyarısı.
    """
    # ---- 1) Yeni SDK şeması: job.dest.* ----
    dest = getattr(job, "dest", None)

    if dest:
        # Inline responses
        inlined = getattr(dest, "inlined_responses", None)
        if inlined:
            # Bu listede öğeler çoğu zaman BatchInlineResponse benzeri objeler (üstünde .response var)
            return list(inlined)

        # File output (tek JSONL dosyası; shard olabilir)
        file_name = getattr(dest, "file_name", None)
        if file_name:
            responses: List[Dict[str, Any]] = []
            try:
                blob = client.files.download(file=file_name)  # arg adı: file=
                data = blob.read() if hasattr(blob, "read") else blob
                text = data.decode("utf-8", errors="replace") if isinstance(data, (bytes, bytearray)) else str(data)
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    try:
                        obj = json.loads(line)
                        responses.append(obj.get("response", obj))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[CHECK][WARN] download failed for dest.file_name '{file_name}': {e}")
            if responses:
                return responses

    # ---- 2) Eski/alternatif şema: job.output.inlined_responses / job.inlined_responses ----
    out = getattr(job, "output", None)
    if out and hasattr(out, "inlined_responses"):
        ir = getattr(out, "inlined_responses")
        res = getattr(ir, "responses", None)
        if res:
            return list(res)
    if hasattr(job, "inlined_responses"):
        ir = getattr(job, "inlined_responses")
        res = getattr(ir, "responses", None)
        if res:
            return list(res)
    if isinstance(job, dict):
        res = (
            (((job.get("output") or {}).get("inlined_responses") or {}).get("responses")) or
            ((job.get("inlined_responses") or {}).get("responses"))
        )
        if res:
            return list(res)

    # ---- 3) Eski/alternatif şema: job.output.files (Files API’de çoklu shard) ----
    files = None
    if out and hasattr(out, "files"):
        files = getattr(out, "files")
    if files is None and isinstance(job, dict):
        files = ((job.get("output") or {}).get("files"))

    if files:
        responses: List[Dict[str, Any]] = []
        for fref in files:
            name = getattr(fref, "name", None) or getattr(fref, "id", None)
            if name is None and isinstance(fref, dict):
                name = fref.get("name") or fref.get("id")
            if not name:
                continue
            try:
                blob = client.files.download(file=name)
                data = blob.read() if hasattr(blob, "read") else blob
                text = data.decode("utf-8", errors="replace") if isinstance(data, (bytes, bytearray)) else str(data)
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    try:
                        obj = json.loads(line)
                        responses.append(obj.get("response", obj))
                    except Exception:
                        pass
            except Exception as e:
                print(f"[CHECK][WARN] download failed for file '{name}': {e}")
        if responses:
            return responses

    # ---- 4) GCS dizini bildirimi (konsol batch gibi) ----
    gcs_dir = None
    if dest and hasattr(dest, "gcs_output_directory"):
        gcs_dir = getattr(dest, "gcs_output_directory")
    if gcs_dir is None and out and hasattr(out, "gcs_output_directory"):
        gcs_dir = getattr(out, "gcs_output_directory")
    if gcs_dir is None and isinstance(job, dict):
        gcs_dir = ((job.get("dest") or {}).get("gcs_output_directory")) or ((job.get("output") or {}).get("gcs_output_directory"))
    if gcs_dir:
        print(f"[CHECK][INFO] Outputs are in GCS: {gcs_dir}")

    return []


def _state_upper(state: Any) -> str:
    return str(state or "").upper()

def _is_succeeded(state: Any) -> bool:
    up = _state_upper(state)
    # JOB_STATE_SUCCEEDED, SUCCEEDED, COMPLETED, DONE gibi varyantları kapsa
    return ("SUCCEEDED" in up) or ("COMPLETED" in up) or ("DONE" in up)

def _is_failed(state: Any) -> bool:
    up = _state_upper(state)
    # JOB_STATE_FAILED / CANCELLED / ERROR gibi varyantları kapsa
    return ("FAILED" in up) or ("CANCEL" in up) or ("ERROR" in up)

def guess_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    if mt is None:
        if path.suffix.lower() == ".wav":
            mt = "audio/wav"
        elif path.suffix.lower() == ".mp3":
            mt = "audio/mp3"
        else:
            mt = "application/octet-stream"
    return mt

def ensure_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        sys.exit("Hata: GEMINI_API_KEY ortam değişkenini ayarla.")
    return key

def write_sibling_txt(audio_path: Path, text: str) -> Path:
    out_path = audio_path.with_suffix(".txt")
    out_path.write_text(text, encoding="utf-8")
    return out_path

def extract_text_from_response(resp_obj: Any) -> str:
    """
    Batch inline yanıtlarında öğe çoğu zaman .response öznitelikli bir wrapper olur.
    Önce onu çöz, sonra GenerateContentResponse / dict şemalarını dolaş.
    """
    # --- YENİ KRİTİK SATIR: wrapper objelerde .response'ı çöz ---
    resp_attr = getattr(resp_obj, "response", None)
    if resp_attr is not None:
        return extract_text_from_response(resp_attr)

    # 0) SDK objesi olabilir (GenerateContentResponse / Candidate / Content / Part ...)
    #    0.a) Kısa yol: .text varsa
    text = getattr(resp_obj, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    #    0.b) GenerateContentResponse -> candidates -> content.parts
    try:
        candidates = getattr(resp_obj, "candidates", None)
        if candidates:
            buf: List[str] = []
            for c in candidates:
                content = getattr(c, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    pt = getattr(p, "text", None)
                    if isinstance(pt, str) and pt.strip():
                        buf.append(pt)
                    inline = getattr(p, "inline_data", None)
                    if inline:
                        mt = getattr(inline, "mime_type", None) or getattr(inline, "mimeType", None)
                        data_b64 = getattr(inline, "data", None)
                        if data_b64 and (mt is None or "text/plain" in str(mt).lower()):
                            try:
                                decoded = base64.b64decode(data_b64).decode("utf-8", errors="replace")
                                if decoded.strip():
                                    buf.append(decoded)
                            except Exception:
                                pass
            if buf:
                return "\n".join(buf).strip()
    except Exception:
        pass

    # 1) dict şemaları
    if isinstance(resp_obj, dict):
        # a) direkt string alanları
        for key in ("text", "output_text", "output"):
            val = resp_obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

        # b) response altına gömülü olabilir
        if "response" in resp_obj and resp_obj["response"]:
            inner = extract_text_from_response(resp_obj["response"])
            if inner:
                return inner

        # c) candidates -> content -> parts[].text
        try:
            cands = resp_obj.get("candidates") or []
            for c in cands:
                parts = (((c or {}).get("content") or {}).get("parts")) or []
                buf = []
                for p in parts:
                    t = p.get("text")
                    if isinstance(t, str) and t.strip():
                        buf.append(t)
                    inline = p.get("inline_data") or p.get("inlineData")
                    if isinstance(inline, dict):
                        mt = inline.get("mime_type") or inline.get("mimeType")
                        data_b64 = inline.get("data")
                        if data_b64 and (mt is None or "text/plain" in str(mt).lower()):
                            try:
                                decoded = base64.b64decode(data_b64).decode("utf-8", errors="replace")
                                if decoded.strip():
                                    buf.append(decoded)
                            except Exception:
                                pass
                if buf:
                    return "\n".join(buf).strip()
        except Exception:
            pass

        # d) prediction alanı
        pred = resp_obj.get("prediction")
        if isinstance(pred, dict):
            inner = extract_text_from_response(pred)
            if inner:
                return inner
        if isinstance(pred, str) and pred.strip():
            return pred.strip()

        # e) safety engeli bilgisi
        pf = resp_obj.get("prompt_feedback") or {}
        if isinstance(pf, dict):
            br = (pf.get("block_reason") or pf.get("blockReason") or "").strip()
            if br:
                return f"[blocked:{br}]"

    # 2) hiçbirinde değilse boş
    return ""

def _norm(p: Path) -> str:
    # Yol karşılaştırmaları için normalize (WSL/OneDrive farklarını azaltır)
    try:
        return p.resolve().as_posix()
    except Exception:
        return str(p)

# -----------------------
# Progress & Pending dosyaları
# -----------------------
def load_progress(progress_file: Path) -> Tuple[set, set]:
    """
    progress.txt formatı:
      DONE|/abs/path/file.wav
      PENDING|/abs/path/file.wav
    Eski tek kolonlu satırlar (yalnız path) DONE sayılır.
    Döndürür: (done_set, pending_set)
    """
    done, pend = set(), set()
    if progress_file.exists():
        for line in progress_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                status, path = line.split("|", 1)
                path = path.strip()
                if status == "DONE":
                    done.add(path)
                elif status == "PENDING":
                    pend.add(path)
            else:
                # backward-compat: tek kolon path => DONE
                done.add(line)
    return done, pend

def append_progress_pending(progress_file: Path, paths: List[Path]) -> None:
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with progress_file.open("a", encoding="utf-8") as f:
        for p in paths:
            f.write(f"PENDING|{_norm(p)}\n")

def mark_progress_done(progress_file: Path, completed_paths: List[Path]) -> None:
    """
    PENDING satırlarını DONE'a çevirir; yoksa DONE ekler.
    Basitçe dosyayı yeniden yazar.
    """
    completed_set = {_norm(p) for p in completed_paths}
    lines: List[str] = []
    if progress_file.exists():
        for line in progress_file.read_text(encoding="utf-8").splitlines():
            if "|" in line:
                status, path = line.split("|", 1)
                path = path.strip()
                if path in completed_set:
                    lines.append(f"DONE|{path}")
                else:
                    lines.append(line)
            else:
                # eski formatı koru
                lines.append(line)
        # Eksik kalanları ekle
        existing_paths = {ln.split("|",1)[1] for ln in lines if "|" in ln}
        for p in completed_set:
            if p not in existing_paths:
                lines.append(f"DONE|{p}")
    else:
        lines = [f"DONE|{p}" for p in completed_set]

    progress_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

def add_job_to_pending_list(pending_file: Path, job_name: str) -> None:
    pending_file.parent.mkdir(parents=True, exist_ok=True)
    with pending_file.open("a", encoding="utf-8") as f:
        f.write(job_name + "\n")

def remove_job_from_pending_list(pending_file: Path, job_name: str) -> None:
    if not pending_file.exists():
        return
    lines = [ln.strip() for ln in pending_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    lines = [ln for ln in lines if ln != job_name]
    pending_file.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

def append_job_to_success_list(success_file: Path, job_name: str) -> None:
    success_file.parent.mkdir(parents=True, exist_ok=True)
    with success_file.open("a", encoding="utf-8") as f:
        f.write(job_name + "\n")

# -----------------------
# Job state (eşleme için)
# -----------------------
def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

def state_path_for_job(job_name: str) -> Path:
    safe = job_name.replace("/", "_")
    return STATE_DIR / f"{safe}.json"

def save_job_state(job_name: str, paths: List[Path], display_name: str) -> None:
    ensure_state_dir()
    data = {
        "job_name": job_name,
        "display_name": display_name,
        "paths": [_norm(p) for p in paths],
        "created_at": int(time.time())
    }
    state_path_for_job(job_name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_job_state(job_name: str) -> Optional[Dict[str, Any]]:
    p = state_path_for_job(job_name)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def delete_job_state(job_name: str) -> None:
    p = state_path_for_job(job_name)
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass

# -----------------------
# Normal (senkron) akış
# -----------------------
def transcribe_file_sync(client: genai.Client, audio_path: Path) -> str:
    if not audio_path.exists():
        raise FileNotFoundError(f"Bulunamadı: {audio_path}")
    mime = guess_mime(audio_path)
    if mime not in SUPPORTED_MIME:
        print(f"[UYARI] Desteklenmeyen MIME: {mime}. Yine de deniyorum...")
    uploaded = client.files.upload(file=str(audio_path))
    resp = client.models.generate_content(
        model=MODEL_ID,
        contents=[PROMPT_TRANSCRIBE, uploaded],
        config=types.GenerateContentConfig(temperature=0, response_mime_type="text/plain"),
    )
    return resp.text or ""

# -----------------------
# Batch (asenkron) akış
# -----------------------
def make_inlined_request_for_audio(client: genai.Client, audio_path: Path) -> Tuple[Dict, Path, str]:
    if not audio_path.exists():
        raise FileNotFoundError(f"Bulunamadı: {audio_path}")
    mime = guess_mime(audio_path)
    uploaded = client.files.upload(file=str(audio_path))
    request = {
        "contents": [
            {"role": "user", "parts": [{"text": PROMPT_TRANSCRIBE}]},
            {"role": "user", "parts": [{
                "file_data": {"file_uri": uploaded.uri, "mime_type": mime}
            }]}
        ],
        "config": {"temperature": 0, "response_mime_type": "text/plain"}
    }
    return request, audio_path, mime

def run_batch_job(client: genai.Client,
                  audio_paths: List[Path],
                  display_name: str,
                  progress_file: Path,
                  pending_file: Path,
                  success_file: Path) -> List[Tuple[Path, str]]:
    inlined_requests = []
    index_to_path: List[Path] = []
    for p in audio_paths:
        req, path, _mime = make_inlined_request_for_audio(client, p)
        inlined_requests.append(req)
        index_to_path.append(path)

    job = client.batches.create(
        model=MODEL_ID,
        src=inlined_requests,                 # doğrudan liste
        config={"display_name": display_name}
    )
    job_name = getattr(job, "name", None) or (getattr(job, "job", None) or "")
    print(f"[BATCH] created: {job_name}  (items={len(inlined_requests)})")

    # 1) Job id'yi kaydet (pending list + state)
    add_job_to_pending_list(pending_file, job_name)
    save_job_state(job_name, index_to_path, display_name)

    # 2) Bu batch'e giren dosyaları PENDING olarak işaretle (yeniden gönderilmesin)
    append_progress_pending(progress_file, index_to_path)

    # 3) Poll with timeout + exponential backoff
    start_ts = time.time()
    sleep_s = 3
    while True:
        if time.time() - start_ts > POLL_TIMEOUT_S:
            raise TimeoutError(f"Batch job timeout (>{POLL_TIMEOUT_S}s): {job_name}")
        time.sleep(sleep_s)
        sleep_s = min(sleep_s * 2, 60)  # 3,6,12,24,48,60...

        try:
            job = client.batches.get(name=job_name)
        except TypeError:
            job = client.batches.get(job_name=job_name)

        state = getattr(job, "state", None) or getattr(job, "status", None) or ""
        details = getattr(job, "status_message", None) or getattr(job, "message", None) or ""
        print(f"[BATCH] state: {state} {('— ' + details) if details else ''}")

        if _is_succeeded(state):
            break
        if _is_failed(state):
            errors = getattr(job, "errors", None) or getattr(job, "error", None)
            raise RuntimeError(f"Batch job failed: state={state}, errors={errors}")

    # 4) Responses çek (inlined_responses yoksa Files API'den JSONL indir)
    responses = _collect_batch_responses(job, client)
    if not responses:
        raise RuntimeError("Batch finished but no responses found (ne inlined_responses ne de files çıktı bulundu).")
    
    if len(responses) != len(index_to_path):
        print(f"[WARN] response count mismatch: responses={len(responses)} vs inputs={len(index_to_path)}")

    # İstenirse ham dump
    if getattr(run_batch_job, "_dump_raw", False):
        raw_path = _dump_raw_jsonl(job_name, responses)
        print(f"[RAW] dumped {len(responses)} responses -> {raw_path}")
        for i, r in enumerate(responses[:5]):
            print(f"[RAW][{i}] {_preview(r)}")

    # 5) Yaz ve ilerlemeyi güncelle
    results: List[Tuple[Path, str]] = []
    completed_paths: List[Path] = []
    for i, resp in enumerate(responses[:len(index_to_path)]):
        orig_path = index_to_path[i]
        text = extract_text_from_response(resp)
        saved = write_sibling_txt(orig_path, text)
        if not (text or "").strip():
            try:
                dbg = saved.with_suffix(saved.suffix + ".resp.json")
                dbg.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[DEBUG] Empty transcript, dumped raw response -> {dbg}")
            except Exception:
                pass

        completed_paths.append(orig_path)
        results.append((orig_path, text))
        print(f"[OK] Saved (batch): {orig_path.with_suffix('.txt')}")

    mark_progress_done(progress_file, completed_paths)
    append_job_to_success_list(success_file, job_name)
    remove_job_from_pending_list(pending_file, job_name)
    delete_job_state(job_name)

    return results

# -----------------------
# Klasör & Checkpoint
# -----------------------
def iter_audio_files(root: Path) -> Iterable[Path]:
    # Büyük ağaçlar için os.walk daha verimli
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in AUDIO_EXTS:
                yield p

def chunked(it: Iterable[Path], n: int) -> Iterable[List[Path]]:
    buf: List[Path] = []
    for x in it:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf

# -----------------------
# Pending kontrol
# -----------------------
def check_pendings_and_finalize(client: genai.Client,
                                progress_file: Path,
                                pending_file: Path,
                                success_file: Path) -> int:
    """
    pending listteki job'ları sorgular.
    SUCCEEDED olanların çıktılarını yazar, progress'i DONE yapar,
    success listesine ekler ve pending listesinden düşer.
    Dönüş: kaç job başarıyla finalize edildi.
    """
    if not pending_file.exists():
        print("[CHECK] No pending file.")
        return 0

    jobs = [ln.strip() for ln in pending_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not jobs:
        print("[CHECK] No pending jobs.")
        return 0

    finalized = 0
    for job_name in jobs:
        print(f"[CHECK] job: {job_name}")
        try:
            try:
                job = client.batches.get(name=job_name)
            except TypeError:
                job = client.batches.get(job_name=job_name)
        except Exception as e:
            print(f"[CHECK][ERR] get failed: {e}")
            continue

        state = getattr(job, "state", None) or getattr(job, "status", None) or ""
        print(f"[CHECK] state: {state}")

        if _is_succeeded(state):
            st = load_job_state(job_name)
            if not st or not st.get("paths"):
                print(f"[CHECK][WARN] state not found for {job_name}, skipping.")
                continue

            index_to_path = [Path(p) for p in st["paths"]]

            responses = _collect_batch_responses(job, client)
            if not responses:
                print(f"[CHECK][ERR] responses not found for {job_name} (ne inlined ne de files)")
                continue
            if len(responses) != len(index_to_path):
                print(f"[CHECK][WARN] response count mismatch: responses={len(responses)} vs inputs={len(index_to_path)}")

            if getattr(check_pendings_and_finalize, "_dump_raw", False):
                raw_path = _dump_raw_jsonl(job_name, responses)
                print(f"[RAW] dumped {len(responses)} responses -> {raw_path}")
                for i, r in enumerate(responses[:5]):
                    print(f"[RAW][{i}] {_preview(r)}")

            completed_paths: List[Path] = []
            for i, resp in enumerate(responses[:len(index_to_path)]):
                ap = index_to_path[i]
                text = extract_text_from_response(resp)
                saved = write_sibling_txt(ap, text)
                if not (text or "").strip():
                    try:
                        dbg = saved.with_suffix(saved.suffix + ".resp.json")
                        dbg.write_text(json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
                        print(f"[DEBUG] Empty transcript, dumped raw response -> {dbg}")
                    except Exception:
                        pass
                
                completed_paths.append(ap)
                print(f"[OK] Saved (check): {ap.with_suffix('.txt')}")

            mark_progress_done(progress_file, completed_paths)
            append_job_to_success_list(success_file, job_name)
            remove_job_from_pending_list(pending_file, job_name)
            delete_job_state(job_name)
            finalized += 1

        elif _is_failed(state):
            print(f"[CHECK][WARN] job failed: {job_name} (state={state})")
        else:
            print(f"[CHECK] still pending: {job_name}")

    print(f"[CHECK] finalized: {finalized}")
    return finalized

# -----------------------
# CLI
# -----------------------
def main(argv: Optional[List[str]] = None) -> int:
    global POLL_TIMEOUT_S

    parser = argparse.ArgumentParser(description="Gemini 2.5 Pro STT (tek/çoklu dosya + opsiyonel Batch + pending takip)")
    parser.add_argument("inputs", nargs="*", help="Ses dosyası yol(ları) (normal mod)")
    parser.add_argument("--use-batch", action="store_true", help="Batch job'larla çalış (klasör gerekir)")
    parser.add_argument("--dir", type=str, help="Batch modda taranacak kök klasör")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch job başına dosya sayısı (default: 100)")
    parser.add_argument("--batch-name", default="transcribe_batch", help="Batch display name prefix")

    parser.add_argument("--progress-file", type=str, default=DEFAULT_PROGRESS_FILE, help="İlerleme dosyası")
    parser.add_argument("--pending-file",  type=str, default=DEFAULT_PENDING_FILE,  help="Bekleyen job id listesi")
    parser.add_argument("--success-file",  type=str, default=DEFAULT_SUCCESS_FILE,  help="Başarıyla tamamlanan job id listesi")

    parser.add_argument("--max-wait", type=int, default=POLL_TIMEOUT_S, help="Batch job başına maksimum bekleme (s)")
    parser.add_argument("--check-pendings", action="store_true", help="Sadece bekleyen job'ları kontrol et ve bitenlerin sonuçlarını yaz")
    parser.add_argument("--dump-raw", action="store_true", help="Ham batch yanıtlarını JSONL olarak kaydet ve konsola özet bas")

    args = parser.parse_args(argv)

    ensure_api_key()
    client = genai.Client()  # GEMINI_API_KEY

    POLL_TIMEOUT_S = int(args.max_wait)

    progress_path = Path(args.progress_file)
    pending_path  = Path(args.pending_file)
    success_path  = Path(args.success_file)

    # ---- Sadece bekleyenleri kontrol et ----
    if args.check_pendings:
        check_pendings_and_finalize._dump_raw = bool(args.dump_raw)
        check_pendings_and_finalize(client, progress_path, pending_path, success_path)
        return 0

    # ---- Batch modu ----
    if args.use_batch:
        if not args.dir:
            sys.exit("Hata: --use-batch ile birlikte --dir vermelisin (içinde ses dosyaları olan klasör).")
        root = Path(args.dir)
        if not root.is_dir():
            sys.exit(f"Hata: klasör bulunamadı: {root}")

        done_set, pend_set = load_progress(progress_path)
        print(f"[INFO] Progress file: {progress_path} (done={len(done_set)}, pending={len(pend_set)})")

        # İşlenmemişleri tara (DONE ya da PENDING olanları atla)
        all_files_iter = (
            p for p in iter_audio_files(root)
            if _norm(p) not in done_set and _norm(p) not in pend_set
        )
        # deterministiklik için sırala (istersen kaldır)
        pending_files = sorted(all_files_iter, key=lambda x: str(x))
        total_pending = len(pending_files)
        print(f"[INFO] Pending files to submit now: {total_pending}")

        batch_idx = 0
        for batch in chunked(pending_files, max(1, args.batch_size)):
            batch_idx += 1
            display = f"{args.batch_name}-{batch_idx:06d}"
            print(f"[BATCH] Submit: {display} (size={len(batch)})")

            try:
                # dump-raw bayrağını fonksiyon attribute'u ile ilet
                run_batch_job._dump_raw = bool(args.dump_raw)
                _ = run_batch_job(
                    client,
                    batch,
                    display_name=display,
                    progress_file=progress_path,
                    pending_file=pending_path,
                    success_file=success_path,
                )
            except Exception as e:
                # Hata politikası: hemen DUR (job id zaten pending listesinde)
                print(f"[WARN] Batch job durduruluyor: {e}")
                return 1

        print("[DONE] Tüm batch'ler gönderildi ve sonuçları alındı (başarılı olanlar).")
        print("Beklemede kalanlar için tekrar:  --check-pendings")
        return 0

    # ---- Normal (senkron) mod ----
    if not args.inputs:
        sys.exit("Hata: normal mod için dosya yolu(ları) ver ya da --use-batch --dir kullan.")

    total = 0
    for p in args.inputs:
        audio = Path(p)
        print(f"[INFO] Transcribing: {audio}")
        try:
            text = transcribe_file_sync(client, audio)
            outp = write_sibling_txt(audio, text)
            print(f"[OK] Saved: {outp}")
            total += 1
        except Exception as e:
            print(f"[ERR] {audio}: {e}")
            # İstersen burada da "hata olursa dur" yapabilirsin:
            # return 1

    print(f"[DONE] {total}/{len(args.inputs)} başarıyla yazıldı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
