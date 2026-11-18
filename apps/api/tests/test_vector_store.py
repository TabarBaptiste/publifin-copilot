import chromadb
import pytest

from config import settings
from rag.chunking import Chunk
from rag.vector_store import (
    AzureSearchStore,
    ChromaStore,
    cosine_distance_from_score,
    get_store,
    search_document_id,
)


def chunk(text, source="a.pdf", page=1, index=0):
    return Chunk(text=text, source=source, page=page, index=index)


def test_chroma_store_returns_the_closest_passage_first():
    store = ChromaStore(chromadb.EphemeralClient())
    store.reset()
    store.add(
        [chunk("proche", page=3), chunk("loin", page=9)],
        [[1.0, 0.0], [0.0, 1.0]],
    )

    passages = store.query([1.0, 0.1], k=2)

    assert store.count() == 2
    assert [(p.text, p.source, p.page) for p in passages] == [
        ("proche", "a.pdf", 3),
        ("loin", "a.pdf", 9),
    ]
    assert passages[0].distance < passages[1].distance


def test_chroma_reset_empties_the_collection():
    store = ChromaStore(chromadb.EphemeralClient())
    store.reset()
    store.add([chunk("x")], [[1.0, 0.0]])

    store.reset()

    assert store.count() == 0


def test_cosine_distance_from_search_score():
    assert cosine_distance_from_score(1.0) == 0.0  # identical vectors
    assert cosine_distance_from_score(0.5) == pytest.approx(1.0)  # orthogonal vectors
    assert cosine_distance_from_score(1 / 3) == pytest.approx(2.0)  # opposite vectors


def test_search_document_id_is_a_valid_azure_key():
    key = search_document_id(chunk("x", source="rgpd.pdf", page=12, index=3))

    assert key.isalnum()
    assert key == search_document_id(chunk("y", source="rgpd.pdf", page=12, index=3))
    assert key != search_document_id(chunk("x", source="rgpd.pdf", page=12, index=4))


class FakeSearchClient:
    def __init__(self, results=()):
        self.uploaded: list[dict] = []
        self.results = list(results)
        self.query_args: dict = {}

    def upload_documents(self, documents):
        self.uploaded.extend(documents)

    def search(self, **kwargs):
        self.query_args = kwargs
        return self.results

    def get_document_count(self):
        return len(self.uploaded)


def test_azure_store_uploads_documents_with_hashed_ids():
    client = FakeSearchClient()
    store = AzureSearchStore(index_client=object(), search_client=client)

    store.add([chunk("texte", source="a.pdf", page=2)], [[0.5, 0.5]])

    document = client.uploaded[0]
    assert document["content"] == "texte"
    assert (document["source"], document["page"]) == ("a.pdf", 2)
    assert document["embedding"] == [0.5, 0.5]
    assert document["id"].isalnum()


def test_azure_store_query_converts_scores_to_distances():
    results = [
        {"content": "t1", "source": "a.pdf", "page": 1, "@search.score": 1.0},
        {"content": "t2", "source": "b.pdf", "page": 5, "@search.score": 0.5},
    ]
    client = FakeSearchClient(results)
    store = AzureSearchStore(index_client=object(), search_client=client)

    passages = store.query([0.1, 0.2], k=2)

    assert [(p.source, p.page, round(p.distance, 3)) for p in passages] == [
        ("a.pdf", 1, 0.0),
        ("b.pdf", 5, 1.0),
    ]
    assert client.query_args["top"] == 2
    assert client.query_args["search_text"] is None


def test_store_follows_the_provider_unless_set_explicitly(monkeypatch):
    monkeypatch.setattr(settings, "vector_store", "")
    monkeypatch.setattr(settings, "llm_provider", "azure_openai")
    monkeypatch.setattr(AzureSearchStore, "__init__", lambda self: None)
    assert isinstance(get_store(), AzureSearchStore)

    monkeypatch.setattr(settings, "vector_store", "inconnu")
    with pytest.raises(ValueError):
        get_store()
