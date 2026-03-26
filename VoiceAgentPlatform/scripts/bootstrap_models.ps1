$ErrorActionPreference = "Stop"

ollama pull gemma3:270m
ollama pull bge-m3:latest

Write-Host "Checking Ollama for a directly usable TTS model..."
$models = ollama list | Out-String
if ($models -match "Orpheus" -or $models -match "tts") {
  Write-Host "Community TTS models may be present, but standard Ollama APIs do not return audio. Defaulting project TTS to Kokoro 82M with espeak-ng as emergency fallback."
} else {
  Write-Host "No usable Ollama-native TTS path detected. Defaulting project TTS to Kokoro 82M with espeak-ng as emergency fallback."
}
