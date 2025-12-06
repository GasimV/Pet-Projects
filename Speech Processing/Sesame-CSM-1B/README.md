# Sesame CSM-1B – Azerbaijani TTS PoC

This folder contains a proof-of-concept fine-tuning of **Sesame CSM-1B** for
Azerbaijani text-to-speech using the notebook `Sesame_CSM_1B_TTS.ipynb`.

## Notebook summary

- Base model: `unsloth/csm-1b` (pre-trained only on English).
- Fine-tuning method: LoRA via Unsloth  
  - `r = 32`, `lora_alpha = 32` on the main attention/MLP projection layers.
- Data: **1128** Azerbaijani audio files (24 kHz) with paired transcripts.
- Audio handling: each clip is truncated or zero-padded to a fixed 15 s
  window (360001 samples) before training.

The goal of this PoC is to see whether an English-only Sesame CSM-1B model can
be adapted to **generate Azerbaijani speech** from a relatively small dataset.
In these experiments, your fine-tuned model is able to produce Azerbaijani
speech, showing that the approach is viable.

## Current limitations & improvement paths

- **More / better data**
  - Collect more high-quality, diverse Azerbaijani recordings (multiple
    speakers, styles, domains).
  - Clean transcripts and remove noisy samples.

- **Stronger training**
  - Try full fine-tuning on a more capable GPU, **or**
  - Keep LoRA but increase capacity (higher rank, higher `lora_alpha`,
    and/or adjusting target modules and hyperparameters).

- **Padding & silence behaviour**
  - Because training uses fixed-length zero-padded audio, the model tends to
    learn long stretches of silence (e.g. ~10 s outputs with only 2–3 s of
    actual speech).
  - Possible fixes:
    - Trim leading/trailing silence from training clips (e.g. with VAD or
      energy-based trimming).
    - Use dynamic padding and mask out padded regions in the loss so the model
      is not rewarded for predicting silence.
    - Reduce the max duration or use smarter chunking so most of each segment
      is real speech.

## Future work

- Add **vLLM** support for Sesame CSM-1B to enable efficient streaming and
  high-concurrency inference, which is important for real-time applications
  such as AI call centers and voicebots.

## Reference

- Sesame CSM research page:  
  <https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice>
