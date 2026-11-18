"""Integration tests against a real PostgreSQL (docker compose up -d db). Skipped if it is down."""

import time
import uuid

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.errors import RaiseException

import main
from agent.audit import AuditEvent, PostgresAuditStore
from agent.db import ensure_schema, make_pool
from agent.graph import Deps, build_graph
from agent.notes import ApprovedNote, PostgresNoteStore
from agent.service import AnalysisService
from tests.test_agent_graph import RULE, FakeProvider, FakeTools


@pytest.fixture(scope="module")
def pool():
    try:
        pool = make_pool()
        ensure_schema(pool)
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"PostgreSQL unavailable: {error!r}")
    yield pool
    pool.close()


def test_audit_log_is_append_only(pool):
    store = PostgresAuditStore(pool)
    run_id = uuid.uuid4().hex
    store.append(
        AuditEvent(run_id, "tool_call", "find_commune", "ok", {"name": "Quimper"}, {"x": 1}, 12)
    )
    store.append(AuditEvent(run_id, "human_decision", "approve", "ok", actor="Baptiste"))

    events = store.list(run_id)

    assert [(e.name, e.actor) for e in events] == [
        ("find_commune", "agent"),
        ("approve", "Baptiste"),
    ]
    assert events[0].input == {"name": "Quimper"} and events[0].duration_ms == 12
    with pool.connection() as conn:
        with pytest.raises(RaiseException, match="append-only"):
            conn.execute("UPDATE audit_events SET status = 'ko' WHERE run_id = %s", (run_id,))
        with pytest.raises(RaiseException, match="append-only"):
            conn.execute("DELETE FROM audit_events WHERE run_id = %s", (run_id,))


def test_notes_are_saved_once_per_run(pool):
    store = PostgresNoteStore(pool)
    run_id = uuid.uuid4().hex
    note = ApprovedNote(run_id, "29232", "Quimper", "Note", "Baptiste", False)

    store.save(note)
    store.save(ApprovedNote(run_id, "29232", "Quimper", "Autre", "Autre", True))

    assert store.get(run_id) == note
    assert store.get("inconnu") is None


def test_full_analysis_through_the_api_with_postgres_checkpoints(pool):
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    audit, notes = PostgresAuditStore(pool), PostgresNoteStore(pool)
    deps = Deps(FakeProvider(), FakeTools(), lambda q: [RULE], audit, notes, {})
    main.app.state.analysis_service = AnalysisService(build_graph(deps, checkpointer), audit)
    try:
        client = TestClient(main.app)
        run_id = client.post(
            "/analyses", json={"request": "Quimper demande 2 M€ pour une école"}
        ).json()["id"]

        view = {}
        for _ in range(50):
            view = client.get(f"/analyses/{run_id}").json()
            if view["status"] != "running":
                break
            time.sleep(0.1)
        assert view["status"] == "awaiting_review"
        assert [s["name"] for s in view["steps"]][-1] == "draft_note"
        assert view["rules"][0]["source"] == "cdc.pdf"
        assert notes.get(run_id) is None  # nothing written yet

        done = client.post(
            f"/analyses/{run_id}/decision", json={"action": "approve", "reviewer": "Baptiste"}
        ).json()

        assert done["status"] == "approved"
        assert notes.get(run_id).reviewer == "Baptiste"
        trail = client.get(f"/analyses/{run_id}/audit").json()
        assert [e["name"] for e in trail][-2:] == ["approve", "save_note"]
        # a second decision is refused: the analysis is over
        again = client.post(
            f"/analyses/{run_id}/decision", json={"action": "reject", "reviewer": "Autre"}
        )
        assert again.status_code == 409
    finally:
        del main.app.state.analysis_service
