#!/usr/bin/env python3
import os
import re
import argparse
from pathlib import Path
from transformers import WhisperTokenizer

# ============================================================================
# 1) TEXT FILTERING LOGIC (from your previous code)
# ============================================================================

CONFUSABLE_MAP = {
    "\u04D8": "\u018F",  # Cyrillic ? -> Latin ?
    "\u04D9": "\u0259",  # Cyrillic ? -> Latin ?
}
CONFUSABLE_RE = re.compile("|".join(map(re.escape, CONFUSABLE_MAP.keys())))

def normalize_confusables(s: str) -> str:
    if not s:
        return s
    return CONFUSABLE_RE.sub(lambda m: CONFUSABLE_MAP[m.group(0)], s)

NON_LATIN_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF"   # Arabic blocks
    r"\u0590-\u05FF"                               # Hebrew
    r"\u0400-\u052F"                               # Cyrillic
    r"\u0370-\u03FF"                               # Greek
    r"\u10A0-\u10FF\u2D00-\u2D2F"                  # Georgian
    r"\u0530-\u058F]"                              # Armenian
)

def looks_azerbaijani_str(t: str) -> bool:
    """Check if text looks like Azerbaijani Latin script."""
    t = normalize_confusables((t or "").strip())
    if len(t) < 2:
        return False
    if NON_LATIN_RE.search(t):
        return False
    # require at least one letter so we don't keep pure digits/punct
    return any(ch.isalpha() for ch in t)

# ============================================================================
# 2) MAIN FILTERING LOGIC
# ============================================================================

def find_audio_text_pairs(folder: Path):
    """Find all .wav and .txt pairs in folder."""
    wav_files = set(folder.rglob("*.wav"))
    txt_files = set(folder.rglob("*.txt"))
    
    pairs = []
    for wav in wav_files:
        txt = wav.with_suffix(".txt")
        if txt in txt_files:
            pairs.append((wav, txt))
    
    return pairs

def should_keep_pair(txt_path: Path, tokenizer, max_length: int):
    """
    Returns (keep: bool, reason: str, text: str, token_count: int)
    """
    try:
        text = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception as e:
        return False, f"Failed to read file: {e}", "", 0
    
    # Check if text looks Azerbaijani
    if not looks_azerbaijani_str(text):
        return False, "Non-Azerbaijani text detected", text, 0
    
    # Check token count
    try:
        tokens = tokenizer(text).input_ids
        token_count = len(tokens)
        
        if token_count > max_length:
            return False, f"Token count ({token_count}) > {max_length}", text, token_count
        
        return True, "OK", text, token_count
    except Exception as e:
        return False, f"Tokenization error: {e}", text, 0

def main():
    ap = argparse.ArgumentParser(
        description="Filter audio-text pairs for Azerbaijani Whisper fine-tuning"
    )
    ap.add_argument("folder", type=Path, 
                    help="Folder containing .wav and .txt pairs")
    ap.add_argument("--model-path", type=str, 
                    default="...",
                    help="Path to your fine-tuned Whisper checkpoint")
    ap.add_argument("--max-length", type=int, default=448,
                    help="Maximum token length (Whisper default: 448)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview what would be deleted without actually deleting")
    ap.add_argument("--execute", action="store_true",
                    help="Actually delete the filtered-out pairs")
    
    args = ap.parse_args()
    
    if not args.folder.is_dir():
        raise SystemExit(f"Not a directory: {args.folder}")
    
    if not args.dry_run and not args.execute:
        raise SystemExit("ERROR: You must specify either --dry-run or --execute")
    
    if args.dry_run and args.execute:
        raise SystemExit("ERROR: Cannot use both --dry-run and --execute together")
    
    # Load tokenizer
    print(f"Loading tokenizer from {args.model_path}...")
    try:
        tokenizer = WhisperTokenizer.from_pretrained(
            args.model_path, 
            language="Azerbaijani", 
            task="transcribe"
        )
    except Exception as e:
        print(f"Failed to load from checkpoint, falling back to base model: {e}")
        tokenizer = WhisperTokenizer.from_pretrained(
            "openai/whisper-large-v3",
            language="Azerbaijani",
            task="transcribe"
        )
    
    print(f"\n{'DRY RUN: ' if args.dry_run else ''}Scanning {args.folder} for audio-text pairs...")
    
    # Find all pairs
    pairs = find_audio_text_pairs(args.folder)
    print(f"Found {len(pairs)} .wav/.txt pairs")
    
    if not pairs:
        print("No pairs found. Nothing to do.")
        return
    
    # Analyze all pairs
    print(f"\nAnalyzing pairs (max_length={args.max_length})...")
    to_keep = []
    to_remove = []
    removal_reasons = {}
    
    for i, (wav, txt) in enumerate(pairs, 1):
        if i % 100 == 0:
            print(f"Analyzed {i}/{len(pairs)} pairs...", flush=True)
        
        keep, reason, text, token_count = should_keep_pair(txt, tokenizer, args.max_length)
        
        if keep:
            to_keep.append((wav, txt))
        else:
            to_remove.append((wav, txt, reason, text, token_count))
            removal_reasons[reason.split('(')[0].strip()] = removal_reasons.get(reason.split('(')[0].strip(), 0) + 1
    
    # Print statistics
    print(f"\n{'='*80}")
    print(f"ANALYSIS RESULTS:")
    print(f"{'='*80}")
    print(f"Total pairs:       {len(pairs)}")
    print(f"Pairs to keep:     {len(to_keep)} ({100*len(to_keep)/len(pairs):.1f}%)")
    print(f"Pairs to remove:   {len(to_remove)} ({100*len(to_remove)/len(pairs):.1f}%)")
    
    if removal_reasons:
        print(f"\nRemoval reasons breakdown:")
        for reason, count in sorted(removal_reasons.items(), key=lambda x: -x[1]):
            print(f"  - {reason}: {count}")
    
    if not to_remove:
        print("\n? No pairs need to be removed!")
        return
    
    # Show examples of what will be removed
    if args.dry_run:
        print(f"\n{'='*80}")
        print(f"DRY RUN: Examples of pairs that would be removed")
        print(f"{'='*80}")
        
        # Show first 10 examples
        for idx, (wav, txt, reason, text, token_count) in enumerate(to_remove[:10], 1):
            print(f"\n[{idx}/{min(10, len(to_remove))}]")
            print(f"WAV: {wav}")
            print(f"TXT: {txt}")
            print(f"Reason: {reason}")
            if text:
                preview = text[:150] + "..." if len(text) > 150 else text
                print(f"Text preview: {preview!r}")
            if token_count > 0:
                print(f"Token count: {token_count}")
        
        if len(to_remove) > 10:
            print(f"\n... and {len(to_remove) - 10} more pairs")
        
        print(f"\n{'='*80}")
        print(f"To actually remove these pairs, run with --execute instead of --dry-run")
        print(f"{'='*80}")
    
    elif args.execute:
        print(f"\n{'='*80}")
        print(f"EXECUTING: Removing {len(to_remove)} pairs")
        print(f"{'='*80}")
        
        removed_wav = 0
        removed_txt = 0
        failed = 0
        
        for i, (wav, txt, reason, _, _) in enumerate(to_remove, 1):
            if i % 100 == 0:
                print(f"Removed {i}/{len(to_remove)} pairs...", flush=True)
            
            try:
                if wav.exists():
                    wav.unlink()
                    removed_wav += 1
                if txt.exists():
                    txt.unlink()
                    removed_txt += 1
            except Exception as e:
                print(f"Failed to remove {wav.stem}: {e}")
                failed += 1
        
        print(f"\n? Successfully removed:")
        print(f"  - {removed_wav} .wav files")
        print(f"  - {removed_txt} .txt files")
        print(f"? Kept {len(to_keep)} pairs")
        if failed > 0:
            print(f"? Failed to remove: {failed} pairs")
    
    print("\nDone!")

if __name__ == "__main__":
    main()