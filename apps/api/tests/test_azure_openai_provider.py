from types import SimpleNamespace

import pytest
from openai import APIConnectionError

from config import settings
from providers import get_provider
from providers.azure_openai import AzureOpenAIProvider
from providers.base import ProviderUnavailable
from providers.ollama import OllamaProvider


class FakeClient:
    def __init__(self, error: Exception | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.error = error
        self.embeddings = SimpleNamespace(create=self._embed)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))

    def _embed(self, **kwargs):
        self._record("embed", kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2]) for _ in kwargs["input"]]
        )

    def _chat(self, **kwargs):
        self._record("chat", kwargs)
        message = SimpleNamespace(content="Réponse [1]")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def _record(self, name, kwargs):
        if self.error:
            raise self.error
        self.calls.append((name, kwargs))


def test_embed_uses_the_embedding_deployment():
    client = FakeClient()

    vectors = AzureOpenAIProvider(client).embed(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.1, 0.2]]
    assert client.calls[0][1]["model"] == settings.azure_openai_embed_deployment


def test_chat_uses_the_chat_deployment_and_returns_the_text():
    client = FakeClient()
    messages = [{"role": "user", "content": "q"}]

    answer = AzureOpenAIProvider(client).chat(messages)

    assert answer == "Réponse [1]"
    assert client.calls[0][1]["model"] == settings.azure_openai_chat_deployment
    assert client.calls[0][1]["messages"] == messages


def test_azure_errors_become_provider_unavailable():
    error = APIConnectionError(request=SimpleNamespace())
    provider = AzureOpenAIProvider(FakeClient(error=error))

    with pytest.raises(ProviderUnavailable):
        provider.chat([{"role": "user", "content": "q"}])
    with pytest.raises(ProviderUnavailable):
        provider.embed(["a"])


def test_warm_up_does_nothing_for_a_hosted_model():
    client = FakeClient()

    AzureOpenAIProvider(client).warm_up()

    assert client.calls == []


def test_provider_is_chosen_by_configuration(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    assert isinstance(get_provider(), OllamaProvider)

    monkeypatch.setattr(settings, "llm_provider", "inconnu")
    with pytest.raises(ValueError):
        get_provider()
