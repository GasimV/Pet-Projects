# =============================================================================
# Input variables — override with terraform.tfvars or -var flags
# =============================================================================
# Defaults match the working Docker Compose / Ollama configuration.
# =============================================================================

variable "llm_provider" {
  description = "LLM provider backend (ollama, openai, huggingface)"
  type        = string
  default     = "ollama"
}

variable "llm_model" {
  description = "Model identifier for the selected LLM provider"
  type        = string
  default     = "gemma3:1b"
}

variable "llm_api_base" {
  description = "Ollama / LLM API endpoint (host.docker.internal reaches the Windows host)"
  type        = string
  default     = "http://host.docker.internal:11434"
}

variable "embedding_provider" {
  description = "Embedding provider (ollama or huggingface)"
  type        = string
  default     = "ollama"
}

variable "embedding_model" {
  description = "Embedding model name (Ollama name, not HuggingFace name)"
  type        = string
  default     = "bge-m3"
}

variable "chunk_size" {
  description = "Document chunk size in tokens"
  type        = number
  default     = 512
}

variable "chunk_overlap" {
  description = "Overlap between consecutive chunks"
  type        = number
  default     = 50
}
