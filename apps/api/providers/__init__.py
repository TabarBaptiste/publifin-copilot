from providers.base import LLMProvider
from providers.ollama import OllamaProvider


def get_provider() -> LLMProvider:
    """Return the configured provider (Azure OpenAI will be added in phase 2)."""
    return OllamaProvider()
