#!/usr/bin/env python3
import argparse, os, sys
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
try:
    # Available in Transformers for OpenAI gpt-oss checkpoints
    from transformers import Mxfp4Config
except Exception:
    Mxfp4Config = None

from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

def bool_flag(x: str) -> bool:
    return str(x).lower() in {"1","true","yes","y","t"}

def main():
    p = argparse.ArgumentParser(description="LoRA SFT for openai/gpt-oss-20b on multilingual reasoning data.")
    # Data & model
    p.add_argument("--dataset", default="HuggingFaceH4/Multilingual-Thinking")
    p.add_argument("--split", default="train")
    p.add_argument("--model", default="openai/gpt-oss-20b")
    p.add_argument("--cache-dir", default=None)
    # Training args (mirroring the tutorial’s spirit)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--per-device-train-batch-size", type=int, default=4)
    p.add_argument("--gradient-accumulation-steps", type=int, default=4)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--warmup-ratio", type=float, default=0.03)
    p.add_argument("--lr-scheduler-type", default="cosine_with_min_lr")
    p.add_argument("--lr-min-rate", type=float, default=0.1)
    p.add_argument("--logging-steps", type=int, default=1)
    p.add_argument("--output-dir", default="gpt-oss-20b-multilingual-reasoner")
    p.add_argument("--report-to", default="trackio")
    p.add_argument("--push-to-hub", action="store_true")
    p.add_argument("--hub-model-id", default=None, help="Optional repo name if pushing to hub.")
    # LoRA
    p.add_argument("--lora-r", type=int, default=8)
    p.add_argument("--lora-alpha", type=int, default=16)
    p.add_argument("--target-modules", default="all-linear")
    p.add_argument("--target-parameters", nargs="*", default=[
        "7.mlp.experts.gate_up_proj",
        "7.mlp.experts.down_proj",
        "15.mlp.experts.gate_up_proj",
        "15.mlp.experts.down_proj",
        "23.mlp.experts.gate_up_proj",
        "23.mlp.experts.down_proj",
    ])
    # Runtime
    p.add_argument("--attn-impl", default="eager")
    p.add_argument("--bf16", type=bool_flag, default=True)
    p.add_argument("--use-mxfp4", type=bool_flag, default=True, help="Use MXFP4 quantization config if available.")
    p.add_argument("--device-map", default="auto")
    p.add_argument("--gradient-checkpointing", type=bool_flag, default=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("[train_lora] configuration:", vars(args))

    if args.dry_run:
        print("[train_lora] DRY RUN: listing planned steps:")
        print("  - load dataset and tokenizer")
        print("  - load base model with eager attention, bf16, MXFP4 (if available)")
        print("  - wrap with PEFT LoRA targeting attention and selected MoE expert projections")
        print("  - run TRL SFT with chat template, push to hub (optional)")
        return

    # Dataset & tokenizer
    ds = load_dataset(args.dataset, split=args.split, cache_dir=args.cache_dir)
    tok = AutoTokenizer.from_pretrained(args.model)

    # Base model + quantization
    quant_cfg = None
    if args.use_mxfp4 and Mxfp4Config is not None:
        quant_cfg = Mxfp4Config(dequantize=True)
        print("[train_lora] Using MXFP4 quantization config.")
    else:
        print("[train_lora] MXFP4 not available or disabled; proceeding without it.")

    model_kwargs = dict(
        attn_implementation=args.attn_impl,
        torch_dtype=torch.bfloat16 if args.bf16 else torch.float32,
        use_cache=False,               # for training + grad checkpointing
        device_map=args.device_map,
    )
    if quant_cfg is not None:
        model_kwargs["quantization_config"] = quant_cfg

    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # LoRA setup
    peft_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=args.target_modules,
        target_parameters=args.target_parameters
    )
    model = get_peft_model(model, peft_cfg)
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    # TRL SFT config
    training_args = SFTConfig(
        learning_rate=args.learning_rate,
        gradient_checkpointing=args.gradient_checkpointing,
        num_train_epochs=args.epochs,
        logging_steps=args.logging_steps,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_length=args.max_length,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type=args.lr_scheduler_type,
        lr_scheduler_kwargs={"min_lr_rate": args.lr_min_rate},
        output_dir=args.output_dir,
        report_to=args.report_to,
        push_to_hub=args.push_to_hub,
        hub_model_id=args.hub_model_id,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=ds,
        processing_class=tok,
    )

    print("[train_lora] starting training…")
    trainer.train()

    print("[train_lora] saving model to", args.output_dir)
    trainer.save_model(args.output_dir)

    if args.push_to_hub:
        print("[train_lora] pushing to hub…")
        trainer.push_to_hub(dataset_name=args.dataset)

    print("[train_lora] done.")

if __name__ == "__main__":
    main()
