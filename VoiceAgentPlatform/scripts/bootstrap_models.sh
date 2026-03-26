#!/usr/bin/env bash
set -euo pipefail

ollama pull gemma3:270m
ollama pull bge-m3:latest

echo "Checking Ollama for a directly usable TTS model..."
if ollama list | grep -Ei 'orpheus|tts' >/dev/null 2>&1; then
  echo "Community TTS models may be present, but standard Ollama APIs do not return audio. Defaulting project TTS to espeak fallback."
else
  echo "No usable Ollama-native TTS path detected. Defaulting project TTS to espeak fallback."
fi

