# %%capture
# import os, re
# if "COLAB_" not in "".join(os.environ.keys()):
#     !pip install unsloth
# else:
#     # Do this only in Colab notebooks! Otherwise use pip install unsloth
#     import torch; v = re.match(r"[0-9]{1,}\.[0-9]{1,}", str(torch.__version__)).group(0)
#     xformers = "xformers==" + ("0.0.33.post1" if v=="2.9" else "0.0.32.post2" if v=="2.8" else "0.0.29.post3")
#     !pip install --no-deps bitsandbytes accelerate {xformers} peft trl triton cut_cross_entropy unsloth_zoo
#     !pip install sentencepiece protobuf "datasets==4.3.0" "huggingface_hub>=0.34.0" hf_transfer
#     !pip install --no-deps unsloth
# !pip install transformers==4.56.2
# !pip install --no-deps trl==0.22.2
# !pip install librosa soundfile evaluate jiwer torchcodec "datasets>=3.4.1,<4.0.0"

# Create virtual environment and run "pip install unsloth" there

from unsloth import FastModel
from transformers import WhisperForConditionalGeneration
import torch

model, tokenizer = FastModel.from_pretrained(
    model_name = "unsloth/whisper-large-v3",
    dtype = None, # Leave as None for auto detection
    load_in_4bit = False, # Set to True to do 4bit quantization which reduces memory
    auto_model = WhisperForConditionalGeneration,
    whisper_language = "English",
    whisper_task = "transcribe",
    # token = "hf_...", # use one if using gated models like meta-llama/Llama-2-7b-hf
)

model = FastModel.get_peft_model(
    model,
    r = 64, # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "v_proj"],
    lora_alpha = 64,
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
    use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
    random_state = 3407,
    use_rslora = False,  # We support rank stabilized LoRA
    loftq_config = None, # And LoftQ
    task_type = None, # ** MUST set this for Whisper **
)

import numpy as np
import tqdm

#Set this to the language you want to train on
model.generation_config.language = "<|en|>"
model.generation_config.task = "transcribe"
model.config.suppress_tokens = []
model.generation_config.forced_decoder_ids = None

def formatting_prompts_func(example):
    audio_arrays = example['audio']['array']
    sampling_rate = example["audio"]["sampling_rate"]
    features = tokenizer.feature_extractor(
        audio_arrays, sampling_rate=sampling_rate
    )
    tokenized_text = tokenizer.tokenizer(example["text"])
    return {
        "input_features": features.input_features[0],
        "labels": tokenized_text.input_ids,
    }
from datasets import load_dataset, Audio
dataset = load_dataset("MrDragonFox/Elise", split="train")

dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
dataset = dataset.train_test_split(test_size=0.06)
train_dataset = [formatting_prompts_func(example) for example in tqdm.tqdm(dataset['train'], desc='Train split')]
test_dataset = [formatting_prompts_func(example) for example in tqdm.tqdm(dataset['test'], desc='Test split')]

# @title Create compute_metrics and datacollator
import evaluate
import torch

from dataclasses import dataclass
from typing import Any, Dict, List, Union
import pdb

metric = evaluate.load("wer")
def compute_metrics(pred):

    pred_logits = pred.predictions[0]
    label_ids = pred.label_ids

    # replace -100 with the pad_token_id
    label_ids[label_ids == -100] = tokenizer.pad_token_id


    pred_ids = np.argmax(pred_logits, axis=-1)

    pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)

    wer = 100 * metric.compute(predictions=pred_str, references=label_str)

    return {"wer": wer}

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:

        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels

        return batch

from transformers import Seq2SeqTrainingArguments, Seq2SeqTrainer
from unsloth import is_bf16_supported
trainer = Seq2SeqTrainer(
    model = model,
    train_dataset = train_dataset,
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=tokenizer),
    eval_dataset = test_dataset,
    tokenizer = tokenizer.feature_extractor,
    compute_metrics=compute_metrics,
    args = Seq2SeqTrainingArguments(
        # predict_with_generate=True,
        per_device_train_batch_size = 1,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        #num_train_epochs = 1, # Set this for 1 full training run.
        max_steps = 60,
        learning_rate = 1e-4,
        logging_steps = 1,
        optim = "adamw_8bit",
        fp16 = not is_bf16_supported(),  # Use fp16 if bf16 is not supported
        bf16 = is_bf16_supported(),  # Use bf16 if supported
        weight_decay = 0.001,
        remove_unused_columns=False,  # required as the PeftModel forward doesn't have the signature of the wrapped model's forward
        lr_scheduler_type = "linear",
        label_names = ['labels'],
        eval_steps = 5 ,
        eval_strategy="steps",
        seed = 3407,
        output_dir = "outputs",
        report_to = "none", # Use TrackIO/WandB etc

    ),
)

# @title Show current memory stats
gpu_stats = torch.cuda.get_device_properties(0)
start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
print(f"{start_gpu_memory} GB of memory reserved.")

trainer_stats = trainer.train()

# @title Show final memory and time stats
used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
used_percentage = round(used_memory / max_memory * 100, 3)
lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
print(
    f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training."
)
print(f"Peak reserved memory = {used_memory} GB.")
print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
print(f"Peak reserved memory % of max memory = {used_percentage} %.")
print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")

model.save_pretrained("lora_model")  # Local saving
tokenizer.save_pretrained("lora_model")