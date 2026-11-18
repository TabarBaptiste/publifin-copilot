"""The pre-analysis agent: a LangGraph workflow with a mandatory human review before any write.

Steps (one node each): extract the request, find the commune, fetch its finances, compute
indicators, search the rules in the corpus, draft the note, pause for the reviewer, record the
decision, save the note (approval or edit only).

The model is used for two steps only (extraction, written appreciation). Tools are called by
fixed code, never chosen by the model: a small local model cannot be trusted with that, and a
fixed path is easier to audit and to bound.
"""

import operator
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from agent.amounts import parse_amount
from agent.audit import AuditEvent, AuditStore
from agent.budget import BudgetedProvider, BudgetExceeded, RunBudget
from agent.indicators import MissingData, compute_indicators
from agent.note import build_note, fr_eur, fr_number
from agent.notes import ApprovedNote, NoteStore
from agent.prompts import (
    appreciation_messages,
    extraction_messages,
    extraction_schema,
)
from agent.schemas import (
    Commune,
    CommuneFinances,
    Decision,
    ExtractedRequest,
    Indicators,
    StepLog,
)
from agent.tools import FinancesInput, GeoLookupInput, PublicDataTools, ToolError, corpus_queries
from config import settings
from providers.base import LLMProvider, ProviderUnavailable
from rag.answer import cited_indices, renumber_citations
from rag.retrieval import Passage

MAX_RULES = 3
RECURSION_LIMIT = 25  # hard cap on the number of graph steps per run

KNOWN_ERRORS = (ToolError, MissingData, BudgetExceeded, ProviderUnavailable, ValueError)


class AnalysisState(TypedDict, total=False):
    run_id: str
    request: str
    requested: dict
    commune: dict
    finances: dict
    indicators: dict
    rules: list[dict]
    draft_note: str
    decision: dict
    outcome: str  # "approved", "rejected" or "failed"
    error: str
    steps: Annotated[list[dict], operator.add]


@dataclass
class Deps:
    provider: LLMProvider
    tools: PublicDataTools
    search: Callable[[str], list[Passage]]  # corpus search, one question -> passages
    audit: AuditStore
    notes: NoteStore
    budgets: dict[str, RunBudget]

    def llm(self, run_id: str) -> BudgetedProvider:
        budget = self.budgets.setdefault(run_id, RunBudget())
        return BudgetedProvider(self.provider, budget)


@dataclass
class Result:
    update: dict
    input: dict | None
    output: dict | None
    summary: str


def passage_to_dict(p: Passage) -> dict:
    return {"text": p.text, "source": p.source, "page": p.page, "distance": p.distance}


def passage_from_dict(d: dict) -> Passage:
    return Passage(**d)


def step(deps: Deps, name: str, kind: str):
    """Wrap a node: time it, write the audit event and the timeline entry, stop the run on error."""

    def decorate(fn: Callable[[AnalysisState], Result]):
        def node(state: AnalysisState) -> dict:
            run_id = state["run_id"]
            started = time.monotonic()
            try:
                result = fn(state)
                status, update = "ok", result.update
                input_, output, summary = result.input, result.output, result.summary
            except KNOWN_ERRORS + (ValidationError,) as error:
                status, input_, output = "error", None, {"error": str(error)}
                summary = str(error)
                update = {"outcome": "failed", "error": summary}
            duration = round((time.monotonic() - started) * 1000)
            deps.audit.append(AuditEvent(run_id, kind, name, status, input_, output, duration))
            log = StepLog(name=name, status=status, duration_ms=duration, summary=summary)
            return {**update, "steps": [log.model_dump()]}

        return node

    return decorate


def parse_extraction(provider: BudgetedProvider, request: str) -> ExtractedRequest:
    """Ask for JSON, validate it, and retry once with the validation error if it is invalid."""
    messages = extraction_messages(request)
    last_error: ValidationError | None = None
    for _ in range(2):
        reply = provider.chat(messages, json_schema=extraction_schema())
        try:
            return ExtractedRequest.model_validate_json(reply)
        except ValidationError as error:
            last_error = error
            messages = messages + [
                {"role": "assistant", "content": reply},
                {
                    "role": "user",
                    "content": f"JSON invalide ({error.error_count()} erreur(s)) : recommence.",
                },
            ]
    raise ValueError(
        "La demande n'a pas pu être comprise : commune introuvable dans le texte."
    ) from last_error


def build_graph(deps: Deps, checkpointer):
    @step(deps, "extract_request", "llm_call")
    def extract_request(state: AnalysisState) -> Result:
        requested = parse_extraction(deps.llm(state["run_id"]), state["request"])
        # Amounts are read by code: the model converts « 2 M€ » unreliably.
        amount = parse_amount(state["request"])
        if amount is not None:
            requested = requested.model_copy(update={"amount_eur": amount})
        return Result(
            {"requested": requested.model_dump()},
            {"request": state["request"]},
            requested.model_dump(),
            f"Commune : {requested.commune_name}, montant : {fr_eur(requested.amount_eur)}",
        )

    @step(deps, "find_commune", "tool_call")
    def find_commune(state: AnalysisState) -> Result:
        requested = ExtractedRequest(**state["requested"])
        query = GeoLookupInput(name=requested.commune_name, department=None)
        commune = deps.tools.find_commune(query)
        return Result(
            {"commune": commune.model_dump()},
            query.model_dump(),
            commune.model_dump(),
            f"{commune.name} ({commune.department}), {commune.population} habitants",
        )

    @step(deps, "get_finances", "tool_call")
    def get_finances(state: AnalysisState) -> Result:
        query = FinancesInput(insee=state["commune"]["insee"])
        finances = deps.tools.get_finances(query)
        return Result(
            {"finances": finances.model_dump()},
            query.model_dump(),
            finances.model_dump(),
            f"Données OFGL {finances.year}, {len(finances.aggregates)} agrégats",
        )

    @step(deps, "compute_indicators", "tool_call")
    def compute(state: AnalysisState) -> Result:
        finances = CommuneFinances(**state["finances"])
        requested = ExtractedRequest(**state["requested"])
        indicators = compute_indicators(finances, requested.amount_eur)
        return Result(
            {"indicators": indicators.model_dump()},
            {"amount_eur": requested.amount_eur},
            indicators.model_dump(),
            f"{len(indicators.alerts)} alerte(s) ; capacité de désendettement : "
            + (
                f"{fr_number(indicators.debt_years)} ans"
                if indicators.debt_years
                else "non calculable"
            ),
        )

    @step(deps, "search_rules", "tool_call")
    def search_rules(state: AnalysisState) -> Result:
        queries = corpus_queries(state["requested"].get("purpose"))
        best: dict[tuple[str, int], Passage] = {}
        for query in queries:
            for passage in deps.search(query):
                if passage.distance > settings.max_distance:
                    continue
                key = (passage.source, passage.page)
                if key not in best or passage.distance < best[key].distance:
                    best[key] = passage
        rules = sorted(best.values(), key=lambda p: p.distance)[:MAX_RULES]
        return Result(
            {"rules": [passage_to_dict(p) for p in rules]},
            {"queries": queries},
            {"passages": [f"{p.source} p.{p.page}" for p in rules]},
            f"{len(rules)} passage(s) retenu(s)",
        )

    @step(deps, "draft_note", "llm_call")
    def draft_note(state: AnalysisState) -> Result:
        commune = Commune(**state["commune"])
        requested = ExtractedRequest(**state["requested"])
        indicators = Indicators(**state["indicators"])
        passages = [passage_from_dict(d) for d in state["rules"]]

        appreciation, cited = "", []
        if passages:
            messages = appreciation_messages(
                commune, indicators, indicators.alerts, requested.purpose, passages
            )
            reply = deps.llm(state["run_id"]).chat(messages).strip()
            cited = cited_indices(reply, len(passages))
            if cited:
                appreciation = renumber_citations(reply, cited)
        if not appreciation:
            # No valid citation: keep only what the code can state, without a model paragraph.
            appreciation = (
                "Aucun commentaire sourcé n'a pu être produit automatiquement : "
                "les alertes ci-dessus sont issues du calcul des indicateurs."
            )
        note = build_note(
            commune, requested, indicators, appreciation, [passages[i - 1] for i in cited]
        )
        return Result(
            {"draft_note": note},
            {"passages": len(passages)},
            {"note_chars": len(note), "citations": cited},
            f"Note de {len(note)} caractères, {len(cited)} source(s) citée(s)",
        )

    def human_review(state: AnalysisState) -> dict:
        # Pauses the graph here. Nothing before this node writes anything; the run resumes only
        # when a person sends a decision through the API.
        decision = interrupt({"draft_note": state["draft_note"]})
        return {"decision": Decision(**decision).model_dump()}

    def record_decision(state: AnalysisState) -> dict:
        decision = Decision(**state["decision"])
        deps.audit.append(
            AuditEvent(
                state["run_id"],
                "human_decision",
                decision.action,
                "ok",
                {"comment": decision.comment, "edited": decision.action == "edit"},
                {"note_chars": len(decision.note or state["draft_note"])},
                None,
                actor=decision.reviewer,
            )
        )
        log = StepLog(
            name="human_decision",
            status="ok",
            duration_ms=0,
            summary=f"{decision.reviewer} : {decision.action}",
        )
        update: dict[str, Any] = {"steps": [log.model_dump()]}
        if decision.action == "reject":
            update["outcome"] = "rejected"
        return update

    @step(deps, "save_note", "tool_call")
    def save_note(state: AnalysisState) -> Result:
        decision = Decision(**state["decision"])
        if decision.action not in ("approve", "edit"):  # defence in depth: reject never saves
            raise ValueError("Enregistrement refusé sans approbation humaine.")
        commune = Commune(**state["commune"])
        text = decision.note if decision.action == "edit" and decision.note else state["draft_note"]
        deps.notes.save(
            ApprovedNote(
                run_id=state["run_id"],
                commune_insee=commune.insee,
                commune_name=commune.name,
                note=text,
                reviewer=decision.reviewer,
                edited=decision.action == "edit",
            )
        )
        return Result(
            {"outcome": "approved"},
            {"reviewer": decision.reviewer},
            {"saved": True},
            "Note enregistrée",
        )

    def stop_on_failure(next_node: str):
        return lambda state: END if state.get("outcome") == "failed" else next_node

    def after_decision(state: AnalysisState) -> str:
        return END if state.get("outcome") == "rejected" else "save_note"

    graph = StateGraph(AnalysisState)
    sequence = [
        ("extract_request", extract_request),
        ("find_commune", find_commune),
        ("get_finances", get_finances),
        ("compute_indicators", compute),
        ("search_rules", search_rules),
        ("draft_note", draft_note),
    ]
    for name, node in sequence:
        graph.add_node(name, node)
    graph.add_node("human_review", human_review)
    graph.add_node("record_decision", record_decision)
    graph.add_node("save_note", save_note)

    graph.add_edge(START, "extract_request")
    names = [name for name, _ in sequence] + ["human_review"]
    for current, following in zip(names, names[1:], strict=False):
        graph.add_conditional_edges(current, stop_on_failure(following), [following, END])
    graph.add_edge("human_review", "record_decision")
    graph.add_conditional_edges("record_decision", after_decision, ["save_note", END])
    graph.add_edge("save_note", END)
    return graph.compile(checkpointer=checkpointer)


def run_config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}, "recursion_limit": RECURSION_LIMIT}
