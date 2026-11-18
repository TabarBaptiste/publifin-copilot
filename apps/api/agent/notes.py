"""Approved notes: the only thing the agent writes, and only after a human decision."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ApprovedNote:
    run_id: str
    commune_insee: str
    commune_name: str
    note: str
    reviewer: str
    edited: bool


class NoteStore(Protocol):
    def save(self, note: ApprovedNote) -> None: ...

    def get(self, run_id: str) -> ApprovedNote | None: ...


@dataclass
class InMemoryNoteStore:
    notes: dict[str, ApprovedNote] = field(default_factory=dict)

    def save(self, note: ApprovedNote) -> None:
        self.notes[note.run_id] = note

    def get(self, run_id: str) -> ApprovedNote | None:
        return self.notes.get(run_id)


class PostgresNoteStore:
    def __init__(self, pool) -> None:
        self._pool = pool

    def save(self, note: ApprovedNote) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO approved_notes"
                " (run_id, commune_insee, commune_name, note, reviewer, edited)"
                " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (run_id) DO NOTHING",
                (
                    note.run_id,
                    note.commune_insee,
                    note.commune_name,
                    note.note,
                    note.reviewer,
                    note.edited,
                ),
            )

    def get(self, run_id: str) -> ApprovedNote | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT run_id, commune_insee, commune_name, note, reviewer, edited"
                " FROM approved_notes WHERE run_id = %s",
                (run_id,),
            ).fetchone()
        return ApprovedNote(**row) if row else None
