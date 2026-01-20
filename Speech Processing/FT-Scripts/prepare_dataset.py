#!/usr/bin/env python3
"""
Step 1: Convert audio-text pairs to HuggingFace Dataset format
"""
import os
import argparse
from pathlib import Path
from datasets import Dataset, Audio
import soundfile as sf

# Set HF cache directories
os.environ["HF_DATASETS_CACHE"] = ".../hf_cache"
os.environ["TRANSFORMERS_CACHE"] = ".../hf_models"
os.environ["HF_HOME"] = ".../hf_home"

def find_audio_text_pairs(folder: Path):
    """Find all .wav and .txt pairs in folder."""
    wav_files = list(folder.rglob("*.wav"))
    
    pairs = []
    for wav in wav_files:
        txt = wav.with_suffix(".txt")
        if txt.exists():
            pairs.append((str(wav), str(txt)))
    
    return pairs

def load_pair(wav_path: str, txt_path: str):
    """Load a single audio-text pair."""
    try:
        # Read text
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # Return path and text (audio will be loaded by datasets.Audio)
        return {
            "audio": wav_path,
            "text": text
        }
    except Exception as e:
        print(f"Error loading pair {wav_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Convert audio-text pairs to HuggingFace Dataset format"
    )
    parser.add_argument("--data-dir", type=str, 
                        default="...",
                        help="Directory containing .wav and .txt pairs")
    parser.add_argument("--output-dir", type=str,
                        default="...",
                        help="Output directory for HF dataset")
    parser.add_argument("--sampling-rate", type=int, default=16000,
                        help="Audio sampling rate")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without creating dataset")
    
    args = parser.parse_args()
    
    data_path = Path(args.data_dir)
    if not data_path.exists():
        raise SystemExit(f"Data directory not found: {args.data_dir}")
    
    print("=" * 80)
    print("STEP 1: Prepare HuggingFace Dataset")
    print("=" * 80)
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Sampling rate: {args.sampling_rate}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print()
    
    # Find all pairs
    print("Scanning for audio-text pairs...")
    pairs = find_audio_text_pairs(data_path)
    print(f"Found {len(pairs)} audio-text pairs")
    
    if len(pairs) == 0:
        raise SystemExit("No audio-text pairs found!")
    
    if args.dry_run:
        print("\n--- DRY RUN: First 10 pairs ---")
        for i, (wav, txt) in enumerate(pairs[:10], 1):
            print(f"\n[{i}] WAV: {wav}")
            print(f"    TXT: {txt}")
            try:
                with open(txt, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"    Text: {preview!r}")
            except Exception as e:
                print(f"    Error reading text: {e}")
        
        if len(pairs) > 10:
            print(f"\n... and {len(pairs) - 10} more pairs")
        
        print("\n" + "=" * 80)
        print("DRY RUN complete. Run without --dry-run to create dataset.")
        print("=" * 80)
        return
    
    # Load all pairs
    print("\nLoading audio-text pairs...")
    data_list = []
    failed = 0
    
    for i, (wav, txt) in enumerate(pairs, 1):
        if i % 100 == 0:
            print(f"Loaded {i}/{len(pairs)} pairs...", flush=True)
        
        pair_data = load_pair(wav, txt)
        if pair_data:
            data_list.append(pair_data)
        else:
            failed += 1
    
    print(f"\nSuccessfully loaded: {len(data_list)} pairs")
    if failed > 0:
        print(f"Failed to load: {failed} pairs")
    
    if len(data_list) == 0:
        raise SystemExit("No valid pairs loaded!")
    
    # Create HuggingFace Dataset
    print("\nCreating HuggingFace Dataset...")
    dataset = Dataset.from_list(data_list)
    
    # Cast audio column to Audio feature
    print(f"Casting audio column to {args.sampling_rate}Hz...")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=args.sampling_rate))
    
    # Save dataset
    print(f"\nSaving dataset to {args.output_dir}...")
    dataset.save_to_disk(args.output_dir)
    
    print("\n" + "=" * 80)
    print("? Dataset preparation complete!")
    print("=" * 80)
    print(f"Dataset saved to: {args.output_dir}")
    print(f"Total samples: {len(dataset)}")
    print(f"\nNext step: Run 2_map_dataset.py")
    print("=" * 80)

if __name__ == "__main__":
    main()