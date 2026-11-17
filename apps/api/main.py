from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from providers import get_provider
from providers.base import LLMProvider, ProviderUnavailable
from rag.answer import answer_question
from rag.retrieval import search

app = FastAPI(title="PubliFin Copilot API")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class Source(BaseModel):
    source: str
    page: int
    extract: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    refused: bool


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
            Source(source=p.source, page=p.page, extract=p.text[:300]) for p in answer.sources
        ],
        refused=answer.refused,
    )
