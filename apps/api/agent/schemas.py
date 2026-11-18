"""Typed data exchanged between the steps of the pre-analysis agent."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedRequest(BaseModel):
    """What the account manager asked, extracted from free text."""

    commune_name: str = Field(min_length=2, max_length=100)
    department: str | None = Field(default=None, description="Département code or name, if given")
    amount_eur: float | None = Field(default=None, ge=0)
    purpose: str | None = Field(default=None, max_length=300)


class Commune(BaseModel):
    name: str
    insee: str
    department: str
    population: int
    homonyms: int = 0  # other communes with the same name (0 = unambiguous)


class CommuneFinances(BaseModel):
    """Main-budget aggregates published by the OFGL for one year."""

    year: int
    population: int
    aggregates: dict[str, float]  # aggregate name -> amount in euros


class Indicators(BaseModel):
    year: int
    population: int
    debt_outstanding_eur: float
    debt_per_capita_eur: float
    gross_savings_eur: float
    gross_savings_rate: float  # gross savings / operating revenue, 0.23 = 23 %
    debt_years: float | None  # outstanding debt / gross savings; None if savings <= 0
    requested_amount_eur: float | None
    debt_years_after: float | None  # same ratio if the whole request were borrowed
    alerts: list[str]


class StepLog(BaseModel):
    name: str
    status: Literal["ok", "error"]
    duration_ms: int
    summary: str


class Decision(BaseModel):
    """The human decision that ends the review."""

    action: Literal["approve", "edit", "reject"]
    reviewer: str = Field(min_length=2, max_length=100)
    note: str | None = Field(default=None, max_length=20000, description="Corrected note (edit)")
    comment: str | None = Field(default=None, max_length=1000)
