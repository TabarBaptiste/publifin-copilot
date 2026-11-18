import logging
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel, Field

from agent.api import router as analyses_router
from agent.audit import PostgresAuditStore
from agent.db import ensure_schema, make_pool
from agent.graph import Deps, build_graph
from agent.notes import PostgresNoteStore
from agent.service import AnalysisService
from agent.tools import PublicDataTools
from config import settings
from providers import get_provider
from providers.base import LLMProvider, ProviderUnavailable
from rag.answer import answer_question
from rag.retrieval import search
from rag.sources import TITLES, page_url

logger = logging.getLogger("uvicorn.error")


def warm_up_models() -> None:
    try:
        get_provider().warm_up()
        logger.info("LLM models loaded")
    except ProviderUnavailable as error:
        logger.warning("LLM warm-up failed, first question will be slower: %s", error)


def init_analyses(app: FastAPI):
    """Connect the pre-analysis agent to PostgreSQL. Without a database, /ask still works."""
    try:
        pool = make_pool()
        ensure_schema(pool)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
    except Exception as error:  # noqa: BLE001 - psycopg/pool errors: the database is optional
        logger.warning("PostgreSQL unavailable, analyses disabled: %r", error)
        return None
    provider = get_provider()
    audit = PostgresAuditStore(pool)
    deps = Deps(
        provider=provider,
        tools=PublicDataTools(),
        search=lambda question: search(question, provider),
        audit=audit,
        notes=PostgresNoteStore(pool),
        budgets={},
    )
    app.state.analysis_service = AnalysisService(build_graph(deps, checkpointer), audit)
    logger.info("Analyses enabled (PostgreSQL)")
    return pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In the background: the API answers /health immediately while models load.
    threading.Thread(target=warm_up_models, daemon=True).start()
    pool = init_analyses(app)
    yield
    if pool:
        pool.close()


app = FastAPI(title="PubliFin Copilot API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class Source(BaseModel):
    source: str
    title: str
    page: int
    extract: str
    url: str | None  # official document, opened at the cited page


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    refused: bool


app.include_router(analyses_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask")
def ask(request: AskRequest, provider: LLMProvider = Depends(get_provider)) -> AskResponse:
    try:
        answer = answer_question(
            request.question, provider, lambda question: search(question, provider)
        )
    except ProviderUnavailable as error:
        raise HTTPException(
            status_code=503, detail="Le modèle de langage est indisponible."
        ) from error
    return AskResponse(
        answer=answer.text,
        sources=[
            Source(
                source=p.source,
                title=TITLES.get(p.source, p.source),
                page=p.page,
                extract=p.text[:300],
                url=page_url(p.source, p.page),
            )
            for p in answer.sources
        ],
        refused=answer.refused,
    )
