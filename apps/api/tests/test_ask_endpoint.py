from fastapi.testclient import TestClient

import main
from providers import get_provider
from rag.retrieval import Passage
from tests.test_answer import FakeProvider


def client_with(provider, monkeypatch, passages):
    monkeypatch.setattr(main, "search", lambda question, provider: passages)
    main.app.dependency_overrides[get_provider] = lambda: provider
    return TestClient(main.app)


def teardown_function():
    main.app.dependency_overrides.clear()


def test_ask_returns_answer_with_citations(monkeypatch):
    passages = [Passage("Le délai est de 72 heures.", "rgpd.pdf", 12, 0.1)]
    client = client_with(FakeProvider("72 heures [1]."), monkeypatch, passages)

    response = client.post("/ask", json={"question": "Quel est le délai ?"})

    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["sources"] == [
        {"source": "rgpd.pdf", "page": 12, "extract": "Le délai est de 72 heures."}
    ]


def test_ask_says_it_cannot_find_when_nothing_is_relevant(monkeypatch):
    client = client_with(
        FakeProvider("x [1]"), monkeypatch, [Passage("hors sujet", "a.pdf", 1, 0.9)]
    )

    body = client.post("/ask", json={"question": "Quelle est la météo ?"}).json()

    assert body["refused"] is True
    assert body["sources"] == []


def test_ask_returns_503_when_the_llm_is_down(monkeypatch):
    client = client_with(FakeProvider(fail=True), monkeypatch, [Passage("t", "a.pdf", 1, 0.1)])

    response = client.post("/ask", json={"question": "Une question ?"})

    assert response.status_code == 503


def test_ask_rejects_too_short_questions(monkeypatch):
    client = client_with(FakeProvider("x"), monkeypatch, [])

    assert client.post("/ask", json={"question": "a"}).status_code == 422
