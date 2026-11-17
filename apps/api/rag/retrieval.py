from dataclasses import dataclass

import chromadb

from config import settings
from providers.base import LLMProvider

COLLECTION = "corpus"


@dataclass(frozen=True)
class Passage:
    text: str
    source: str
    page: int
    distance: float  # cosine distance: 0 = identical, larger = less related


def search(question: str, provider: LLMProvider, k: int | None = None) -> list[Passage]:
    """Return the passages closest to the question, best first."""
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    collection = client.get_collection(COLLECTION)
    result = collection.query(
        query_embeddings=provider.embed([question]),
        n_results=k or settings.top_k,
    )
    return [
        Passage(text=text, source=meta["source"], page=meta["page"], distance=distance)
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
        )
    ]
