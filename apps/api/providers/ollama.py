import httpx

from config import settings
from providers.base import ProviderUnavailable


class OllamaProvider:
    """LLM provider backed by a local Ollama server."""

    def _post(self, path: str, payload: dict, timeout: float) -> dict:
        try:
            response = httpx.post(
                f"{settings.ollama_base_url}{path}", json=payload, timeout=timeout
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ProviderUnavailable(f"Ollama: {error!r}") from error
        return response.json()

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": settings.ollama_embed_model, "input": texts}
        return self._post("/api/embed", payload, timeout=300)["embeddings"]

    def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": settings.ollama_chat_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.1, "num_ctx": settings.chat_context_tokens},
        }
        return self._post("/api/chat", payload, timeout=settings.chat_timeout_seconds)["message"][
            "content"
        ]
