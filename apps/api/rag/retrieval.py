from config import settings
from providers.base import LLMProvider
from rag.vector_store import Passage, get_store

__all__ = ["Passage", "search"]


def search(question: str, provider: LLMProvider, k: int | None = None) -> list[Passage]:
    """Return the passages closest to the question, best first."""
    embedding = provider.embed([question])[0]
    return get_store().query(embedding, k or settings.top_k)
