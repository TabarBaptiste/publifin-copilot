"""HTTP endpoints of the pre-analysis agent."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from agent.schemas import Decision
from agent.service import AnalysisService, AnalysisView, NotAwaitingReview

router = APIRouter(prefix="/analyses", tags=["analyses"])


def get_service(request: Request) -> AnalysisService:
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(503, "Base de données indisponible : analyses désactivées.")
    return service


Service = Annotated[AnalysisService, Depends(get_service)]


class StartRequest(BaseModel):
    request: str = Field(min_length=10, max_length=1000)


class StartResponse(BaseModel):
    id: str


class AuditItem(BaseModel):
    kind: str
    name: str
    status: str
    actor: str
    duration_ms: int | None
    input: dict | None
    output: dict | None


@router.post("", status_code=202)
def start_analysis(body: StartRequest, service: Service) -> StartResponse:
    return StartResponse(id=service.start(body.request))


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, service: Service) -> AnalysisView:
    view = service.get(analysis_id)
    if view is None:
        raise HTTPException(404, "Analyse introuvable.")
    return view


@router.post("/{analysis_id}/decision")
def decide(analysis_id: str, decision: Decision, service: Service) -> AnalysisView:
    if decision.action == "edit" and not (decision.note and decision.note.strip()):
        raise HTTPException(422, "Une note corrigée est nécessaire pour l'action « edit ».")
    try:
        return service.decide(analysis_id, decision)
    except NotAwaitingReview:
        raise HTTPException(409, "Cette analyse n'attend pas de décision.") from None


@router.get("/{analysis_id}/audit")
def audit_trail(analysis_id: str, service: Service) -> list[AuditItem]:
    return [
        AuditItem(
            kind=e.kind,
            name=e.name,
            status=e.status,
            actor=e.actor,
            duration_ms=e.duration_ms,
            input=e.input,
            output=e.output,
        )
        for e in service.audit_trail(analysis_id)
    ]
