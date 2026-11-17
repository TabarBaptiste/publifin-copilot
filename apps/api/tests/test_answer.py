from providers.base import ProviderUnavailable
from rag.answer import NOT_FOUND, answer_question, build_messages, cited_indices
from rag.retrieval import Passage


class FakeProvider:
    def __init__(self, reply: str = "", fail: bool = False):
        self.reply = reply
        self.fail = fail
        self.calls = 0

    def embed(self, texts):
        return [[0.0] for _ in texts]

    def chat(self, messages):
        self.calls += 1
        if self.fail:
            raise ProviderUnavailable("down")
        return self.reply


def passage(text="texte", source="a.pdf", page=1, distance=0.2):
    return Passage(text=text, source=source, page=page, distance=distance)


def test_cited_indices_keeps_valid_numbers_in_order_without_duplicates():
    assert cited_indices("A [2] puis B [1][2] et C [9] [0]", count=3) == [2, 1]


def test_prompt_numbers_the_passages_and_contains_the_question():
    messages = build_messages(
        "Quelle durée ?", [passage("un", "a.pdf", 3), passage("deux", "b.pdf", 7)]
    )

    assert messages[0]["role"] == "system"
    assert "[1] (a.pdf, page 3)\nun" in messages[1]["content"]
    assert "[2] (b.pdf, page 7)\ndeux" in messages[1]["content"]
    assert messages[1]["content"].endswith("Question : Quelle durée ?")


def test_refuses_without_calling_the_llm_when_no_passage_is_close_enough():
    provider = FakeProvider(reply="Réponse [1]")

    answer = answer_question("q", provider, lambda _: [passage(distance=0.95)])

    assert answer.refused and answer.text == NOT_FOUND and answer.sources == []
    assert provider.calls == 0


def test_answer_returns_only_cited_sources():
    provider = FakeProvider(reply="La durée est de 5 ans [2].")
    passages = [passage("x", "a.pdf", 1), passage("y", "b.pdf", 9)]

    answer = answer_question("q", provider, lambda _: passages)

    assert not answer.refused
    assert [(s.source, s.page) for s in answer.sources] == [("b.pdf", 9)]


def test_refuses_when_the_answer_has_no_valid_citation():
    provider = FakeProvider(reply="Je pense que c'est 5 ans.")

    answer = answer_question("q", provider, lambda _: [passage()])

    assert answer.refused and answer.text == NOT_FOUND


def test_refuses_when_the_model_says_it_does_not_know():
    provider = FakeProvider(reply=NOT_FOUND)

    answer = answer_question("q", provider, lambda _: [passage()])

    assert answer.refused
