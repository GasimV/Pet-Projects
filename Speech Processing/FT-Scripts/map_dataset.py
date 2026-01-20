#!/usr/bin/env python3
"""
Step 2: Map dataset - extract features and tokenize labels
"""
import os
import argparse
import torch
from datasets import load_from_disk, Audio, DatasetDict
from transformers import (
    WhisperFeatureExtractor,
    WhisperTokenizer,
    WhisperProcessor,
    WhisperForConditionalGeneration
)

# Set HF cache directories
os.environ["HF_DATASETS_CACHE"] = ".../hf_cache"
os.environ["TRANSFORMERS_CACHE"] = ".../hf_models"
os.environ["HF_HOME"] = ".../hf_home"

def prepare_batch(batch, feature_extractor, tokenizer):
    """Extract features and tokenize text."""
    arrays = [a["array"] for a in batch["audio"]]
    feats = feature_extractor(arrays, sampling_rate=16000).input_features
    labels = tokenizer(batch["text"]).input_ids
    return {"input_features": feats, "labels": labels}

def main():
    parser = argparse.ArgumentParser(
        description="Map dataset: extract features and tokenize"
    )
    parser.add_argument("--input-dir", type=str, default="...", help="Input HF dataset directory")
    parser.add_argument("--output-dir", type=str, default="...", help="Output directory for mapped dataset")
    parser.add_argument("--tokenizer-path", type=str, default="...", help="Path to the fine-tuned tokenizer")
    parser.add_argument("--model-path", type=str, default="...", help="Path to fine-tuned Whisper checkpoint")
    parser.add_argument("--max-length", type=int, default=448, help="Maximum token length")
    parser.add_argument("--test-size", type=float, default=0.005, help="Test split size (default: 0.005 = 0.5%)")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for mapping")
    parser.add_argument("--num-proc", type=int, default=None, help="Number of processes (default: cpu_count//2)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without processing")
    
    args = parser.parse_args()
    
    if args.num_proc is None:
        args.num_proc = max(1, os.cpu_count() // 2)
    
    print("=" * 80)
    print("STEP 2: Map Dataset (Extract Features & Tokenize)")
    print("=" * 80)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Tokenizer path: {args.tokenizer_path}")
    print(f"Model path: {args.model_path}")
    print(f"Max token length: {args.max_length}")
    print(f"Test split size: {args.test_size}")
    print(f"Batch size: {args.batch_size}")
    print(f"Num processes: {args.num_proc}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")
    print()
    
    # Load dataset
    print("Loading dataset...")
    ds = load_from_disk(args.input_dir)
    print(f"Loaded {len(ds)} samples")

    # Load tokenizer and feature extractor
    print("\nLoading tokenizer and feature extractor...")
    try:
        # --- USE THE NEW TOKENIZER PATH ---
        print(f"  Trying tokenizer from: {args.tokenizer_path}")
        tokenizer = WhisperTokenizer.from_pretrained(
            args.tokenizer_path,
            language="Azerbaijani",
            task="transcribe"
        )
        feature_extractor = WhisperFeatureExtractor.from_pretrained(args.tokenizer_path)
        print("  ? Loaded from fine-tuned tokenizer path")
    except Exception as e:
        print(f"  Warning: Could not load from tokenizer path ({e})")
        print("  Falling back to base model tokenizer...")
        tokenizer = WhisperTokenizer.from_pretrained(
            "openai/whisper-large-v3",
            language="Azerbaijani",
            task="transcribe"
        )
        feature_extractor = WhisperFeatureExtractor.from_pretrained("openai/whisper-large-v3")
        print("  ? Loaded base model tokenizer")
    
    if args.dry_run:
        print("\n--- DRY RUN: First 3 samples ---")
        for i, ex in enumerate(ds.select(range(min(3, len(ds)))), 1):
            print(f"\n[{i}]")
            audio_path = ex['audio']['path'] if isinstance(ex['audio'], dict) else ex['audio']
            print(f"Audio path: {audio_path}")
            print(f"Text: {ex['text'][:100]}..." if len(ex['text']) > 100 else f"Text: {ex['text']}")
        
        print("\n" + "=" * 80)
        print("DRY RUN complete. Run without --dry-run to process dataset.")
        print("=" * 80)
        return

    # --- If not a dry run, now we cast the column for processing ---
    print("\nCasting audio column to 16kHz...")
    ds = ds.cast_column("audio", Audio(sampling_rate=16_000))
    
    # Map dataset
    # ... (the rest of the script is the same) ...
    print("\nMapping dataset (extracting features & tokenizing)...")
    proc = ds.map(
        lambda batch: prepare_batch(batch, feature_extractor, tokenizer),
        remove_columns=ds.column_names,
        batched=True,
        batch_size=args.batch_size,
        num_proc=args.num_proc,
        desc="Mapping"
    )
    print(f"Mapped {len(proc)} samples")
    
    # Filter by max length
    print(f"\nFiltering samples with labels <= {args.max_length} tokens...")
    filtered = proc.filter(
        lambda ex: len(ex["labels"]) <= args.max_length,
        num_proc=args.num_proc,
        desc="Filtering"
    )
    print(f"Kept {len(filtered)}/{len(proc)} samples ({100*len(filtered)/len(proc):.1f}%)")
    removed = len(proc) - len(filtered)
    if removed > 0:
        print(f"Removed {removed} samples exceeding max length")
    
    # Split into train/test
    print(f"\nSplitting into train/test (test_size={args.test_size})...")
    splits = filtered.train_test_split(test_size=args.test_size, seed=42)
    dd = DatasetDict(train=splits["train"], test=splits["test"])
    
    print(f"Train samples: {len(dd['train'])}")
    print(f"Test samples: {len(dd['test'])}")
    
    # Save dataset
    print(f"\nSaving mapped dataset to {args.output_dir}...")
    dd.save_to_disk(args.output_dir)
    
    print("\n" + "=" * 80)
    print("? Dataset mapping complete!")
    print("=" * 80)
    print(f"Dataset saved to: {args.output_dir}")
    print(f"Train samples: {len(dd['train'])}")
    print(f"Test samples: {len(dd['test'])}")
    print(f"\nNext step: Run 3_finetune.py")
    print("=" * 80)

if __name__ == "__main__":
    main()