from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from providers import get_provider
from providers.base import LLMProvider, ProviderUnavailable
from rag.answer import answer_question
from rag.retrieval import search
from rag.sources import SOURCES, TITLES

app = FastAPI(title="PubliFin Copilot API")
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


def page_url(source: str, page: int) -> str | None:
    url = SOURCES.get(source)
    return f"{url}#page={page}" if url else None


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
