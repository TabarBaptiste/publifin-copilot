import httpx

from config import settings


def embed(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per text, computed by the local Ollama server."""
    response = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json={"model": settings.ollama_embed_model, "input": texts},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["embeddings"]
