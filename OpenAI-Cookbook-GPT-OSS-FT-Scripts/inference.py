#!/usr/bin/env python3
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def main():
    p = argparse.ArgumentParser(description="Run multilingual reasoning inference with a reasoning-language system prompt.")
    p.add_argument("--model", default="gpt-oss-20b-multilingual-reasoner-merged", help="Merged model directory or Hub id.")
    p.add_argument("--reasoning-language", default="German")
    p.add_argument("--user-prompt", default="¿Cuál es el capital de Australia?")
    p.add_argument("--max-new-tokens", type=int, default=512)
    p.add_argument("--temperature", type=float, default=0.6)
    p.add_argument("--top-p", type=float, default=None)
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--device-map", default="auto")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("[inference] model:", args.model)
    print("[inference] reasoning_language:", args.reasoning_language)
    print("[inference] user_prompt:", args.user_prompt)
    if args.dry_run:
        print("[inference] DRY RUN: would load model, format Harmony chat, and generate.")
        return

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, attn_implementation="eager", torch_dtype="auto", use_cache=True, device_map=args.device_map
    )

    system_prompt = f"reasoning language: {args.reasoning_language}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": args.user_prompt},
    ]

    input_ids = tok.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    gen_kwargs = dict(
        max_new_tokens=args.max_new_tokens,
        do_sample=True,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
    )

    with torch.no_grad():
        out = model.generate(input_ids, **gen_kwargs)

    decoded = tok.batch_decode(out)[0]
    print("\n[inference] raw output:\n")
    print(decoded)

if __name__ == "__main__":
    main()
