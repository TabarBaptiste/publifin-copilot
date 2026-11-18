"""PostgreSQL connection pool and schema (audit log, approved notes)."""

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL,
    input       JSONB,
    output      JSONB,
    duration_ms INTEGER,
    actor       TEXT NOT NULL DEFAULT 'agent',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_events_run ON audit_events (run_id, id);

-- The log is append-only: any UPDATE or DELETE is refused.
CREATE OR REPLACE FUNCTION audit_events_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_events_no_change ON audit_events;
CREATE TRIGGER audit_events_no_change BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_immutable();

CREATE TABLE IF NOT EXISTS approved_notes (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL UNIQUE,
    commune_insee TEXT NOT NULL,
    commune_name  TEXT NOT NULL,
    note          TEXT NOT NULL,
    reviewer      TEXT NOT NULL,
    edited        BOOLEAN NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def make_pool() -> ConnectionPool:
    pool = ConnectionPool(
        settings.database_url,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    )
    pool.open(wait=True, timeout=5)  # fails fast (PoolTimeout) when the database is down
    return pool


def ensure_schema(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        conn.execute(SCHEMA)
