"""Audit log: every tool call and every human decision is recorded, never modified."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AuditEvent:
    run_id: str
    kind: str  # "tool_call", "llm_call" or "human_decision"
    name: str
    status: str  # "ok" or "error"
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    duration_ms: int | None = None
    actor: str = "agent"  # the reviewer's name for human decisions


class AuditStore(Protocol):
    def append(self, event: AuditEvent) -> None: ...

    def list(self, run_id: str) -> list[AuditEvent]: ...


@dataclass
class InMemoryAuditStore:
    events: list[AuditEvent] = field(default_factory=list)

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)

    def list(self, run_id: str) -> list[AuditEvent]:
        return [e for e in self.events if e.run_id == run_id]


class PostgresAuditStore:
    def __init__(self, pool) -> None:
        self._pool = pool

    def append(self, event: AuditEvent) -> None:
        from psycopg.types.json import Jsonb

        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO audit_events"
                " (run_id, kind, name, status, input, output, duration_ms, actor)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    event.run_id,
                    event.kind,
                    event.name,
                    event.status,
                    Jsonb(event.input) if event.input is not None else None,
                    Jsonb(event.output) if event.output is not None else None,
                    event.duration_ms,
                    event.actor,
                ),
            )

    def list(self, run_id: str) -> list[AuditEvent]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT run_id, kind, name, status, input, output, duration_ms, actor"
                " FROM audit_events WHERE run_id = %s ORDER BY id",
                (run_id,),
            ).fetchall()
        return [AuditEvent(**row) for row in rows]
