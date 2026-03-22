# =============================================================================
# Input variables — override with terraform.tfvars or -var flags
# =============================================================================

variable "llm_provider" {
  description = "LLM provider backend (huggingface, openai, ollama)"
  type        = string
  default     = "huggingface"
}

variable "llm_model" {
  description = "Model identifier for the selected LLM provider"
  type        = string
  default     = "google/gemma-3-1b-it"
}

variable "embedding_model" {
  description = "HuggingFace embedding model name"
  type        = string
  default     = "BAAI/bge-m3"
}
