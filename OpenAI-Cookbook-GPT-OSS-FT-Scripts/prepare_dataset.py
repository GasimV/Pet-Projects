#!/usr/bin/env python3
import argparse, json, os, sys
from datasets import load_dataset
from transformers import AutoTokenizer

def main():
    p = argparse.ArgumentParser(description="Inspect and format the multilingual reasoning dataset.")
    p.add_argument("--dataset", default="HuggingFaceH4/Multilingual-Thinking")
    p.add_argument("--split", default="train")
    p.add_argument("--sample-index", type=int, default=0)
    p.add_argument("--tokenizer", default="openai/gpt-oss-20b")
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"[prepare_dataset] dataset={args.dataset} split={args.split} cache_dir={args.cache_dir}")
    if args.dry_run:
        print("[prepare_dataset] DRY RUN: skipping dataset download.")
        return

    ds = load_dataset(args.dataset, split=args.split, cache_dir=args.cache_dir)
    print(f"[prepare_dataset] loaded {len(ds)} rows")

    # Show the raw example
    idx = max(0, min(args.sample_index, len(ds)-1))
    ex = ds[idx]
    print("[prepare_dataset] raw example keys:", list(ex.keys()))
    if "messages" in ex:
        print("[prepare_dataset] messages schema example:")
        print(json.dumps(ex["messages"], ensure_ascii=False, indent=2))

    # Show how the tokenizer renders Harmony chat format
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    messages = ex["messages"] if "messages" in ex else [
        {"role": "user", "content": "¿Cuál es el capital de Australia?"}
    ]
    rendered = tok.apply_chat_template(messages, tokenize=False)
    print("\n[prepare_dataset] rendered chat template preview:\n")
    print(rendered[:1500] + ("\n... [truncated]" if len(rendered) > 1500 else ""))

if __name__ == "__main__":
    main()
