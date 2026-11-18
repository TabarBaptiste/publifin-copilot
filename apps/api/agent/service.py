"""Runs analyses in the background and exposes their state, built from the graph checkpoints."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from langgraph.types import Command
from pydantic import BaseModel

from agent.audit import AuditEvent, AuditStore
from agent.graph import run_config
from agent.schemas import Decision, StepLog
from rag.sources import TITLES, page_url

Status = Literal["running", "awaiting_review", "approved", "rejected", "failed"]


class RuleSource(BaseModel):
    source: str
    title: str
    page: int
    extract: str
    url: str | None


class AnalysisView(BaseModel):
    id: str
    status: Status
    request: str
    steps: list[StepLog]
    commune: dict | None = None
    indicators: dict | None = None
    rules: list[RuleSource] = []
    draft_note: str | None = None
    error: str | None = None


class NotAwaitingReview(Exception):
    """A decision was sent for an analysis that is not waiting for one."""


class AnalysisService:
    def __init__(self, graph, audit: AuditStore) -> None:
        self._graph = graph
        self._audit = audit
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def start(self, request: str) -> str:
        run_id = uuid.uuid4().hex
        with self._lock:
            self._active.add(run_id)
        self._executor.submit(self._run, run_id, request)
        return run_id

    def _run(self, run_id: str, request: str) -> None:
        try:
            self._graph.invoke({"run_id": run_id, "request": request}, run_config(run_id))
        except Exception as error:  # noqa: BLE001 - any crash must end up in the audit log
            self._audit.append(
                AuditEvent(run_id, "run", "crashed", "error", None, {"error": repr(error)})
            )
        finally:
            with self._lock:
                self._active.discard(run_id)

    def get(self, run_id: str) -> AnalysisView | None:
        snapshot = self._graph.get_state(run_config(run_id))
        values = snapshot.values
        if not values:
            with self._lock:
                started = run_id in self._active
            return self._view(run_id, {"request": ""}, "running") if started else None

        if values.get("outcome"):
            status: Status = values["outcome"]
        elif any(task.interrupts for task in snapshot.tasks):
            status = "awaiting_review"
        else:
            with self._lock:
                alive = run_id in self._active
            # Not finished and not running any more: the process stopped (crash, restart).
            status = "running" if alive else "failed"
        return self._view(run_id, values, status)

    def decide(self, run_id: str, decision: Decision) -> AnalysisView:
        view = self.get(run_id)
        if view is None or view.status != "awaiting_review":
            raise NotAwaitingReview(run_id)
        self._graph.invoke(Command(resume=decision.model_dump()), run_config(run_id))
        return self.get(run_id)

    def audit_trail(self, run_id: str) -> list[AuditEvent]:
        return self._audit.list(run_id)

    @staticmethod
    def _view(run_id: str, values: dict, status: Status) -> AnalysisView:
        error = values.get("error")
        if status == "failed" and not error:
            error = "Analyse interrompue avant la fin."
        return AnalysisView(
            id=run_id,
            status=status,
            request=values.get("request", ""),
            steps=[StepLog(**s) for s in values.get("steps", [])],
            commune=values.get("commune"),
            indicators=values.get("indicators"),
            rules=[
                RuleSource(
                    source=r["source"],
                    title=TITLES.get(r["source"], r["source"]),
                    page=r["page"],
                    extract=r["text"][:300],
                    url=page_url(r["source"], r["page"]),
                )
                for r in values.get("rules", [])
            ],
            draft_note=values.get("draft_note"),
            error=error,
        )
