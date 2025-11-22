#!/usr/bin/env python3
import argparse, os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    p = argparse.ArgumentParser(description="Merge LoRA weights into base model for fast inference.")
    p.add_argument("--base-model", default="openai/gpt-oss-20b")
    p.add_argument("--peft-id", default="gpt-oss-20b-multilingual-reasoner", help="Local path or Hub repo id with LoRA weights.")
    p.add_argument("--output-dir", default="gpt-oss-20b-multilingual-reasoner-merged")
    p.add_argument("--device-map", default="auto")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print(f"[merge] base={args.base_model} peft={args.peft_id} out={args.output_dir}")
    if args.dry_run:
        print("[merge] DRY RUN: would load base + LoRA and merge, then save.")
        return

    tok = AutoTokenizer.from_pretrained(args.base_model)
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model, attn_implementation="eager", torch_dtype="auto", use_cache=True, device_map=args.device_map
    )
    peft_model = PeftModel.from_pretrained(base, args.peft_id)
    merged = peft_model.merge_and_unload()
    os.makedirs(args.output_dir, exist_ok=True)
    print("[merge] saving merged model and tokenizer…")
    merged.save_pretrained(args.output_dir)
    tok.save_pretrained(args.output_dir)
    print("[merge] done.")

if __name__ == "__main__":
    main()
