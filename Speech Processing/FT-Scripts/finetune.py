#!/usr/bin/env python3
"""
Step 3: Fine-tune Whisper model on mapped dataset
"""
import os
import argparse
import torch
import evaluate
from datasets import load_from_disk
from transformers import (
    WhisperFeatureExtractor,
    WhisperTokenizer,
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer
)
from dataclasses import dataclass
from typing import Any, Dict, List, Union

# Set HF cache directories
os.environ["HF_DATASETS_CACHE"] = ".../hf_cache"
os.environ["TRANSFORMERS_CACHE"] = ".../hf_models"
os.environ["HF_HOME"] = ".../hf_home"

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any
    
    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        inputs = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(inputs, return_tensors="pt")
        
        label_features = [{"input_ids": f["labels"]} for f in features]
        label_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = label_batch["input_ids"].masked_fill(label_batch.attention_mask.ne(1), -100)
        
        # Drop leading BOS if present everywhere
        if labels.numel() > 0 and (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        
        batch["labels"] = labels
        return batch

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune Whisper model"
    )
    parser.add_argument("--data-dir", type=str, default="...", help="Mapped dataset directory")
    parser.add_argument("--tokenizer-path", type=str, default="...", help="Path to the fine-tuned tokenizer")
    parser.add_argument("--model-path", type=str, default="...", help="Path to fine-tuned Whisper checkpoint to continue from")
    parser.add_argument("--output-dir", type=str, default="...", help="Output directory for fine-tuned model")
    parser.add_argument("--smoke-test", action="store_true", help="Run quick smoke test (50 steps)")
    parser.add_argument("--per-device-train-batch-size", type=int, default=48, help="Training batch size per device")
    parser.add_argument("--per-device-eval-batch-size", type=int, default=74, help="Evaluation batch size per device")
    parser.add_argument("--learning-rate", type=float, default=1e-5, help="Learning rate")
    parser.add_argument("--num-train-epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--dataloader-num-workers", type=int, default=4, help="Number of dataloader workers")
    parser.add_argument("--logging-steps", type=int, default=100, help="Log every N steps")
    parser.add_argument("--dry-run", action="store_true", help="Show configuration without training")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("STEP 3: Fine-tune Whisper Model")
    print("=" * 80)
    print(f"Data directory: {args.data_dir}")
    print(f"Tokenizer path: {args.tokenizer_path}")
    print(f"Model path: {args.model_path}")
    print(f"Output directory: {args.output_dir}")
    print(f"Smoke test: {args.smoke_test}")
    print(f"Training batch size: {args.per_device_train_batch_size}")
    print(f"Eval batch size: {args.per_device_eval_batch_size}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Epochs: {args.num_train_epochs}")
    print(f"Dataloader workers: {args.dataloader_num_workers}")
    print(f"Logging steps: {args.logging_steps}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Compute Capability: {torch.cuda.get_device_capability(0)}")
    
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print()
    
    # Load dataset
    print("Loading dataset...")
    dd = load_from_disk(args.data_dir)
    train_ds = dd["train"]
    eval_ds = dd["test"]
    print(f"Train samples: {len(train_ds)}")
    print(f"Test samples: {len(eval_ds)}")
    
    if args.dry_run:
        print("\n--- DRY RUN: Dataset info ---")
        print(f"Train features: {train_ds.features}")
        print(f"First train sample keys: {list(train_ds[0].keys())}")
        print(f"Input features shape: {len(train_ds[0]['input_features'])}")
        print(f"Labels length: {len(train_ds[0]['labels'])}")
        
        print("\n" + "=" * 80)
        print("DRY RUN complete. Run without --dry-run to start training.")
        print("=" * 80)
        return
    
    # Load tokenizer, feature extractor, and processor
    print("\nLoading tokenizer, feature extractor, and processor...")
    try:
        print(f"  Trying tokenizer from: {args.tokenizer_path}")
        tokenizer = WhisperTokenizer.from_pretrained(
            args.tokenizer_path,
            language="Azerbaijani",
            task="transcribe"
        )
        feature_extractor = WhisperFeatureExtractor.from_pretrained(args.tokenizer_path)
        processor = WhisperProcessor.from_pretrained(
            args.tokenizer_path,
            language="Azerbaijani",
            task="transcribe"
        )
        print("  ? Loaded from checkpoint")
    except Exception as e:
        print(f"  Warning: {e}")
        print("  Falling back to base model...")
        tokenizer = WhisperTokenizer.from_pretrained(
            "openai/whisper-large-v3",
            language="Azerbaijani",
            task="transcribe"
        )
        feature_extractor = WhisperFeatureExtractor.from_pretrained("openai/whisper-large-v3")
        processor = WhisperProcessor.from_pretrained(
            "openai/whisper-large-v3",
            language="Azerbaijani",
            task="transcribe"
        )
        print("  ? Loaded base model processor")
    
    # Load model
    print("\nLoading model...")
    print(f"  Loading from: {args.model_path}")
    model = WhisperForConditionalGeneration.from_pretrained(args.model_path)
    model.generation_config.language = "az"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    model.generation_config.suppress_tokens = []
    print("  ? Model loaded")
    
    # Data collator
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)
    
    # Compute metrics
    print("\nLoading WER metric...")
    wer_metric = evaluate.load("wer")
    
    def compute_metrics(pred):
        pred_ids, label_ids = pred.predictions, pred.label_ids
        label_ids = label_ids.copy()
        label_ids[label_ids == -100] = tokenizer.pad_token_id
        pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        return {"wer": 100 * wer_metric.compute(predictions=pred_str, references=label_str)}

    
    # Training arguments
    print("\nConfiguring training arguments...")
    use_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
    
    if args.smoke_test:
        print("  Using SMOKE TEST configuration (50 steps)")
        training_args = Seq2SeqTrainingArguments(
            output_dir=args.output_dir + "_smoke",
            per_device_train_batch_size=8,
            per_device_eval_batch_size=4,
            learning_rate=args.learning_rate,
            max_steps=50,
            eval_strategy="steps",
            eval_steps=25,
            save_steps=25,
            logging_steps=10,
            fp16=torch.cuda.is_available() and not use_bf16,
            bf16=use_bf16,
            predict_with_generate=True,
            generation_max_length=225,
            load_best_model_at_end=True,
            metric_for_best_model="wer",
            greater_is_better=False,
            push_to_hub=False,
        )
    else:
        print(f"  Using FULL TRAINING configuration ({args.num_train_epochs} epochs)")
        training_args = Seq2SeqTrainingArguments(
            output_dir=args.output_dir,
            per_device_train_batch_size=args.per_device_train_batch_size,
            per_device_eval_batch_size=args.per_device_eval_batch_size,
            learning_rate=args.learning_rate,
            num_train_epochs=args.num_train_epochs,
            #eval_strategy="no",
            eval_strategy="epoch",
            save_strategy="epoch",
            logging_steps=args.logging_steps,
            bf16=use_bf16,
            fp16=(not use_bf16) and torch.cuda.is_available(),
            predict_with_generate=True,
            generation_max_length=225,
            load_best_model_at_end=True,
            metric_for_best_model="wer",
            greater_is_better=False,
            dataloader_num_workers=args.dataloader_num_workers,
            group_by_length=False,
            remove_unused_columns=False,
            push_to_hub=False,
        )
    
    print(f"  FP16: {training_args.fp16}")
    print(f"  BF16: {training_args.bf16}")
    print(f"  Eval strategy: {training_args.eval_strategy}")
    
    # Trainer
    print("\nInitializing trainer...")
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        tokenizer=processor.feature_extractor,
        compute_metrics=compute_metrics,
    )
    
    # Save processor
    print(f"\nSaving processor to {training_args.output_dir}...")
    processor.save_pretrained(training_args.output_dir)
    
    # Train
    print("\n" + "=" * 80)
    print("Starting training...")
    print("=" * 80)
    trainer.train()
    
    print("\n" + "=" * 80)
    print("? Training complete!")
    print("=" * 80)
    print(f"Model saved to: {training_args.output_dir}")
    print("=" * 80)

if __name__ == "__main__":
    main()