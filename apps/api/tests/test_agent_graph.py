import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.audit import InMemoryAuditStore
from agent.graph import Deps, build_graph, run_config
from agent.notes import InMemoryNoteStore
from agent.schemas import Commune, CommuneFinances
from agent.tools import ToolError
from providers.base import ProviderUnavailable
from rag.retrieval import Passage

QUIMPER = Commune(name="Quimper", insee="29232", department="Finistère", population=64385)
FINANCES = CommuneFinances(
    year=2025,
    population=66725,
    aggregates={
        "Encours de dette": 59_701_543.0,
        "Epargne brute": 18_422_833.0,
        "Recettes de fonctionnement": 79_246_796.0,
    },
)
RULE = Passage("Seuil d'alerte de 7 % des produits de fonctionnement.", "cdc.pdf", 57, 0.2)
EXTRACTION = {
    "commune_name": "Quimper",
    "department": None,
    "amount_eur": 2_000_000,
    "purpose": "rénovation d'une école",
}


class FakeProvider:
    def __init__(self, extraction=None, appreciation="Le seuil est de 7 % [1]."):
        self.extraction = json.dumps(EXTRACTION if extraction is None else extraction)
        self.appreciation = appreciation
        self.json_calls = 0

    def chat(self, messages, json_schema=None):
        if json_schema:
            self.json_calls += 1
            return self.extraction
        return self.appreciation

    def embed(self, texts):
        return [[0.0] for _ in texts]

    def warm_up(self):
        pass


class FakeTools:
    def __init__(self, geo_error=None):
        self.geo_error = geo_error

    def find_commune(self, query):
        if self.geo_error:
            raise self.geo_error
        return QUIMPER

    def get_finances(self, query):
        return FINANCES


def make_graph(provider=None, tools=None, rules=(RULE,), budget_tokens=None):
    deps = Deps(
        provider=provider or FakeProvider(),
        tools=tools or FakeTools(),
        search=lambda question: list(rules),
        audit=InMemoryAuditStore(),
        notes=InMemoryNoteStore(),
        budgets={},
    )
    if budget_tokens:
        from agent.budget import RunBudget

        deps.budgets["run-1"] = RunBudget(max_tokens=budget_tokens)
    return build_graph(deps, MemorySaver()), deps


def start(graph):
    config = run_config("run-1")
    graph.invoke({"run_id": "run-1", "request": "Quimper demande 2 M€ pour une école."}, config)
    return config


def awaiting_review(graph, config) -> bool:
    return any(task.interrupts for task in graph.get_state(config).tasks)


def step_names(graph, config):
    return [s["name"] for s in graph.get_state(config).values["steps"]]


def test_run_stops_for_review_after_drafting_and_writes_nothing():
    graph, deps = make_graph()

    config = start(graph)

    assert awaiting_review(graph, config)
    assert step_names(graph, config) == [
        "extract_request",
        "find_commune",
        "get_finances",
        "compute_indicators",
        "search_rules",
        "draft_note",
    ]
    note = graph.get_state(config).values["draft_note"]
    assert "Quimper" in note and "3,2 ans" in note and "[1] " in note
    assert deps.notes.notes == {}  # nothing saved before a human decides
    assert [e.name for e in deps.audit.list("run-1")] == step_names(graph, config)


def test_approval_saves_the_note_and_audits_the_reviewer():
    graph, deps = make_graph()
    config = start(graph)

    graph.invoke(Command(resume={"action": "approve", "reviewer": "Baptiste"}), config)

    values = graph.get_state(config).values
    assert values["outcome"] == "approved"
    saved = deps.notes.get("run-1")
    assert saved.reviewer == "Baptiste" and saved.edited is False
    assert saved.note == values["draft_note"]
    decision = [e for e in deps.audit.list("run-1") if e.kind == "human_decision"]
    assert [(e.name, e.actor) for e in decision] == [("approve", "Baptiste")]


def test_edit_saves_the_corrected_note():
    graph, deps = make_graph()
    config = start(graph)

    graph.invoke(
        Command(resume={"action": "edit", "reviewer": "Baptiste", "note": "Note corrigée"}), config
    )

    saved = deps.notes.get("run-1")
    assert saved.note == "Note corrigée" and saved.edited is True


def test_rejection_never_saves():
    graph, deps = make_graph()
    config = start(graph)

    graph.invoke(Command(resume={"action": "reject", "reviewer": "Baptiste"}), config)

    assert graph.get_state(config).values["outcome"] == "rejected"
    assert deps.notes.notes == {}
    assert "save_note" not in step_names(graph, config)
    assert [e.name for e in deps.audit.list("run-1") if e.kind == "human_decision"] == ["reject"]


def test_a_tool_error_stops_the_run_before_any_write():
    graph, deps = make_graph(tools=FakeTools(geo_error=ToolError("Commune introuvable")))

    config = start(graph)

    values = graph.get_state(config).values
    assert values["outcome"] == "failed" and "introuvable" in values["error"]
    assert step_names(graph, config) == ["extract_request", "find_commune"]
    assert not awaiting_review(graph, config)
    assert deps.notes.notes == {}
    assert [e.status for e in deps.audit.list("run-1")] == ["ok", "error"]


def test_invalid_extraction_is_retried_once_then_fails():
    provider = FakeProvider(extraction={"commune_name": "", "amount_eur": -5})
    graph, _ = make_graph(provider=provider)

    config = start(graph)

    assert provider.json_calls == 2
    assert graph.get_state(config).values["outcome"] == "failed"


def test_token_budget_stops_the_run():
    graph, _ = make_graph(budget_tokens=10)

    config = start(graph)

    values = graph.get_state(config).values
    assert values["outcome"] == "failed" and "Budget" in values["error"]


def test_llm_outage_is_reported_as_a_failed_step():
    class Down(FakeProvider):
        def chat(self, messages, json_schema=None):
            raise ProviderUnavailable("Ollama arrêté")

    graph, _ = make_graph(provider=Down())

    config = start(graph)

    assert graph.get_state(config).values["outcome"] == "failed"


def test_note_without_valid_citation_falls_back_to_computed_content():
    graph, _ = make_graph(provider=FakeProvider(appreciation="Tout va bien."))

    config = start(graph)

    note = graph.get_state(config).values["draft_note"]
    assert "Aucun commentaire sourcé" in note
    assert "## Sources documentaires" not in note


def test_far_passages_are_ignored():
    graph, _ = make_graph(rules=[Passage("hors sujet", "a.pdf", 1, 0.9)])

    config = start(graph)

    assert graph.get_state(config).values["rules"] == []


@pytest.mark.parametrize("action", ["approve", "edit"])
def test_decision_requires_a_reviewer_name(action):
    graph, deps = make_graph()
    config = start(graph)

    with pytest.raises(ValueError):
        graph.invoke(Command(resume={"action": action, "reviewer": ""}), config)

    assert deps.notes.notes == {}


def test_amount_is_read_from_the_text_even_if_the_model_misses_it():
    provider = FakeProvider(extraction={**EXTRACTION, "amount_eur": None})
    graph, _ = make_graph(provider=provider)

    config = start(graph)  # request: "Quimper demande 2 M€ pour une école."

    assert graph.get_state(config).values["requested"]["amount_eur"] == 2_000_000
    assert "**Demande** : 2,0 M€" in graph.get_state(config).values["draft_note"]
