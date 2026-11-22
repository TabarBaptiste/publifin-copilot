"""Vector stores: local Chroma files, or Azure AI Search in the cloud.

Both expose the same three operations, so ingestion and retrieval do not depend on the backend.
Vectors from different embedding models are not comparable: each backend has its own index.
"""

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from config import settings
from rag.chunking import Chunk

COLLECTION = "corpus"


@dataclass(frozen=True)
class Passage:
    text: str
    source: str
    page: int
    distance: float  # cosine distance: 0 = identical, larger = less related


class VectorStore(Protocol):
    def reset(self) -> None:
        """Create an empty index, replacing any previous one."""
        ...

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...

    def query(self, embedding: list[float], k: int) -> list[Passage]:
        """The k closest passages, best first."""
        ...

    def count(self) -> int: ...


class ChromaStore:
    def __init__(self, client: Any | None = None) -> None:
        import chromadb

        self._client = client or chromadb.PersistentClient(path=str(settings.vector_store_dir))

    def reset(self) -> None:
        if COLLECTION in [c.name for c in self._client.list_collections()]:
            self._client.delete_collection(COLLECTION)
        self._client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        self._client.get_collection(COLLECTION).add(
            ids=[f"{c.source}:{c.page}:{c.index}" for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[{"source": c.source, "page": c.page} for c in chunks],
        )

    def query(self, embedding: list[float], k: int) -> list[Passage]:
        result = self._client.get_collection(COLLECTION).query(
            query_embeddings=[embedding], n_results=k
        )
        return [
            Passage(text=text, source=meta["source"], page=meta["page"], distance=distance)
            for text, meta, distance in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
            )
        ]

    def count(self) -> int:
        return self._client.get_collection(COLLECTION).count()


def search_document_id(chunk: Chunk) -> str:
    """Azure AI Search keys only allow letters, digits, '_', '-' and '=': hash the readable id."""
    return hashlib.sha1(f"{chunk.source}:{chunk.page}:{chunk.index}".encode()).hexdigest()


def cosine_distance_from_score(score: float) -> float:
    """Azure AI Search scores cosine matches as 1 / (1 + distance): invert it.

    Source: learn.microsoft.com/azure/search/vector-search-ranking (to confirm on first real run).
    """
    return (1 - score) / score


class AzureSearchStore:
    """Azure AI Search index with a vector field, authenticated with Entra ID (no key)."""

    def __init__(self, index_client: Any | None = None, search_client: Any | None = None) -> None:
        if index_client is None or search_client is None:
            from azure.identity import DefaultAzureCredential
            from azure.search.documents import SearchClient
            from azure.search.documents.indexes import SearchIndexClient

            credential = DefaultAzureCredential()
            index_client = index_client or SearchIndexClient(
                settings.azure_search_endpoint, credential
            )
            search_client = search_client or SearchClient(
                settings.azure_search_endpoint, settings.azure_search_index, credential
            )
        self._index_client = index_client
        self._search_client = search_client

    def reset(self) -> None:
        from azure.search.documents.indexes.models import (
            HnswAlgorithmConfiguration,
            HnswParameters,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            SearchIndex,
            SimpleField,
            VectorSearch,
            VectorSearchProfile,
        )

        index = SearchIndex(
            name=settings.azure_search_index,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(
                    name="content", type=SearchFieldDataType.String, analyzer_name="fr.microsoft"
                ),
                SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=settings.embedding_dimensions,
                    vector_search_profile_name="hnsw-cosine",
                    # Never read back: not storing the raw copy halves the vector storage
                    # (~11 MB for 1 760 chunks), which matters on the 50 MB free tier.
                    stored=False,
                ),
            ],
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="hnsw", parameters=HnswParameters(metric="cosine")
                    )
                ],
                profiles=[
                    VectorSearchProfile(name="hnsw-cosine", algorithm_configuration_name="hnsw")
                ],
            ),
        )
        self._index_client.create_or_update_index(index)
        # create_or_update keeps old documents: empty the index so it matches the corpus folder.
        old = [{"id": r["id"]} for r in self._search_client.search("*", select=["id"], top=100000)]
        if old:
            self._search_client.delete_documents(old)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        documents = [
            {
                "id": search_document_id(c),
                "content": c.text,
                "source": c.source,
                "page": c.page,
                "embedding": vector,
            }
            for c, vector in zip(chunks, embeddings, strict=True)
        ]
        self._search_client.upload_documents(documents)

    def query(self, embedding: list[float], k: int) -> list[Passage]:
        from azure.search.documents.models import VectorizedQuery

        results = self._search_client.search(
            search_text=None,
            vector_queries=[
                VectorizedQuery(vector=embedding, k_nearest_neighbors=k, fields="embedding")
            ],
            select=["content", "source", "page"],
            top=k,
        )
        return [
            Passage(
                text=r["content"],
                source=r["source"],
                page=r["page"],
                distance=cosine_distance_from_score(r["@search.score"]),
            )
            for r in results
        ]

    def count(self) -> int:
        return self._search_client.get_document_count()


def get_store() -> VectorStore:
    backend = settings.vector_store or (
        "azure_search" if settings.llm_provider == "azure_openai" else "chroma"
    )
    if backend == "azure_search":
        return AzureSearchStore()
    if backend == "chroma":
        return ChromaStore()
    raise ValueError(f"Unknown VECTOR_STORE: {backend!r}")
