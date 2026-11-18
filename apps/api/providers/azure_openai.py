from typing import Any

from azure.core.exceptions import AzureError
from azure.identity import (
    CredentialUnavailableError,
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from openai import AzureOpenAI, OpenAIError

from config import settings
from providers.base import ProviderUnavailable

TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureOpenAIProvider:
    """LLM provider backed by Azure OpenAI, authenticated with Entra ID (no API key).

    Locally, DefaultAzureCredential uses your `az login`; on Azure, the Container App's
    managed identity.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
            azure_ad_token_provider=get_bearer_token_provider(
                DefaultAzureCredential(), TOKEN_SCOPE
            ),
            timeout=settings.chat_timeout_seconds,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(
                model=settings.azure_openai_embed_deployment, input=texts
            )
        except (OpenAIError, AzureError, CredentialUnavailableError) as error:
            raise ProviderUnavailable(f"Azure OpenAI: {error!r}") from error
        return [item.embedding for item in response.data]

    def chat(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=settings.azure_openai_chat_deployment, messages=messages, temperature=0.1
            )
        except (OpenAIError, AzureError, CredentialUnavailableError) as error:
            raise ProviderUnavailable(f"Azure OpenAI: {error!r}") from error
        return response.choices[0].message.content or ""

    def warm_up(self) -> None:
        """Nothing to load: the models are hosted by Azure."""
