from config import settings
from providers.base import LLMProvider


def get_provider() -> LLMProvider:
    """Return the provider selected by LLM_PROVIDER (SDKs are imported only when used)."""
    if settings.llm_provider == "azure_openai":
        from providers.azure_openai import AzureOpenAIProvider

        return AzureOpenAIProvider()
    if settings.llm_provider == "ollama":
        from providers.ollama import OllamaProvider

        return OllamaProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
