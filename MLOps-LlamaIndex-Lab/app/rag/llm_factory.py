"""
Pluggable LLM factory.

Returns a LlamaIndex LLM instance based on the configured provider.
Adding a new provider is as simple as adding another branch here.
"""

from llama_index.core.llms import LLM

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_llm() -> LLM:
    """Instantiate the LLM backend selected via ``LLM_PROVIDER``."""
    provider = settings.llm_provider.lower()
    logger.info("Initialising LLM  provider=%s  model=%s", provider, settings.llm_model)

    if provider == "huggingface":
        from llama_index.llms.huggingface import HuggingFaceLLM

        return HuggingFaceLLM(
            model_name=settings.llm_model,
            tokenizer_name=settings.llm_model,
            device_map="auto",
            # Reasonable defaults for a small instruct model
            generate_kwargs={"temperature": 0.7, "do_sample": True, "max_new_tokens": 512},
        )

    if provider == "openai":
        from llama_index.llms.openai import OpenAI

        return OpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )

    if provider == "ollama":
        from llama_index.llms.ollama import Ollama

        return Ollama(
            model=settings.llm_model,
            base_url=settings.llm_api_base,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        "Supported: huggingface, openai, ollama."
    )
