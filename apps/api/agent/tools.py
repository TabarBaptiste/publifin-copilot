"""Read-only tools of the agent. Each one has a strict input schema and no write access."""

import re
import unicodedata

import httpx
from pydantic import BaseModel, ConfigDict, Field

from agent.indicators import REQUIRED_AGGREGATES
from agent.schemas import Commune, CommuneFinances

GEO_URL = "https://geo.api.gouv.fr/communes"
OFGL_URL = "https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/ofgl-base-communes/records"


class ToolError(Exception):
    """A tool could not produce a usable result (message is shown to the reviewer)."""


class GeoLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    department: str | None = Field(default=None, pattern=r"^(\d{2,3}|2[AB])$")


class FinancesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insee: str = Field(pattern=r"^(\d{5}|2[AB]\d{3})$")


def _normalize(text: str) -> str:
    """Lowercase, no accents, punctuation as spaces: 'Fort-de-France' == 'fort de france'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


class PublicDataTools:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=30)

    def _get(self, url: str, params: dict) -> dict | list:
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            raise ToolError(f"Service public indisponible ({url}) : {error!r}") from error

    def find_commune(self, query: GeoLookupInput) -> Commune:
        """API Géo (geo.api.gouv.fr): identity and population of a commune."""
        params = {"nom": query.name, "fields": "nom,code,population,departement", "limit": 10}
        if query.department and len(query.department) <= 3 and query.department[0:2].isdigit():
            params["codeDepartement"] = query.department
        results = self._get(GEO_URL, params)
        wanted = _normalize(query.name)
        exact = [r for r in results if _normalize(r["nom"]) == wanted and "population" in r]
        if not exact:
            raise ToolError(f"Commune introuvable : « {query.name} ».")
        best = max(exact, key=lambda r: r["population"])
        return Commune(
            name=best["nom"],
            insee=best["code"],
            department=best["departement"]["nom"],
            population=best["population"],
            homonyms=len(exact) - 1,
        )

    def get_finances(self, query: FinancesInput) -> CommuneFinances:
        """OFGL open data: main-budget aggregates of the latest available year."""
        where = f'insee="{query.insee}" AND type_de_budget="Budget principal"'
        latest = self._get(
            OFGL_URL, {"where": where, "select": "exer", "order_by": "exer desc", "limit": 1}
        )
        if not latest["results"]:
            raise ToolError(f"Aucune donnée financière publique pour la commune {query.insee}.")
        year = int(latest["results"][0]["exer"][:4])

        names = ",".join(f'"{name}"' for name in REQUIRED_AGGREGATES)
        records = self._get(
            OFGL_URL,
            {
                "where": f"{where} AND year(exer)={year} AND agregat IN ({names})",
                "select": "agregat,montant,ptot",
                "limit": 20,
            },
        )["results"]
        if not records:
            raise ToolError(f"Données {year} incomplètes pour la commune {query.insee}.")
        return CommuneFinances(
            year=year,
            population=int(records[0]["ptot"]),
            aggregates={r["agregat"]: float(r["montant"]) for r in records},
        )


def corpus_queries(purpose: str | None) -> list[str]:
    """Fixed questions put to the document corpus: the agent never lets a model write them."""
    queries = [
        "seuil d'alerte de l'épargne brute des communes",
        "seuil d'alerte de l'endettement des communes en années d'épargne brute",
    ]
    if purpose:
        queries.append(f"financement des collectivités : {purpose}")
    return queries
