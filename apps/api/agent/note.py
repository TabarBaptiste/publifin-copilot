"""Assembles the pre-analysis note. Figures come from code, never from the language model."""

from agent.indicators import fr
from agent.schemas import Commune, ExtractedRequest, Indicators
from rag.retrieval import Passage
from rag.sources import TITLES


def fr_number(value: float, decimals: int = 1) -> str:
    return fr(value, decimals)


def fr_eur(amount: float | None) -> str:
    if amount is None:
        return "non précisé"
    if abs(amount) >= 1_000_000:
        return f"{fr(amount / 1_000_000)} M€"
    return f"{amount:,.0f} €".replace(",", " ")


def build_note(
    commune: Commune,
    request: ExtractedRequest,
    indicators: Indicators,
    appreciation: str,
    passages: list[Passage],
) -> str:
    """Markdown note. `passages` are the sources cited by `appreciation`, numbered [1], [2]..."""
    i = indicators
    lines = [
        f"# Pré-analyse : {commune.name} ({commune.department})",
        "",
        f"**Demande** : {fr_eur(request.amount_eur)}"
        + (f" — {request.purpose}" if request.purpose else ""),
        "",
        f"## Situation financière (OFGL, budget principal {i.year})",
        f"- Population : {i.population:,} habitants".replace(",", " "),
        f"- Encours de dette : {fr_eur(i.debt_outstanding_eur)} "
        f"({fr_number(i.debt_per_capita_eur, 0)} € par habitant)",
        f"- Épargne brute : {fr_eur(i.gross_savings_eur)} "
        f"({fr_number(i.gross_savings_rate * 100)} % des recettes de fonctionnement)",
    ]
    if i.debt_years is None:
        lines.append(
            "- Capacité de désendettement : non calculable (épargne brute nulle ou négative)"
        )
    else:
        line = f"- Capacité de désendettement : {fr_number(i.debt_years)} ans"
        if i.debt_years_after is not None:
            after = fr_number(i.debt_years_after)
            line += f" ({after} ans si la totalité de la demande était empruntée)"
        lines.append(line)
    if commune.homonyms:
        lines.append(
            f"- ⚠ {commune.homonyms} autre(s) commune(s) portent le même nom : "
            "la plus peuplée a été retenue, à vérifier."
        )

    lines += ["", "## Points d'attention"]
    lines += [f"- {alert}" for alert in i.alerts]
    lines += ["", appreciation.strip()]

    if passages:
        lines += ["", "## Sources documentaires"]
        for number, passage in enumerate(passages, start=1):
            title = TITLES.get(passage.source, passage.source)
            lines.append(f"- [{number}] {title}, page {passage.page}")

    lines += [
        "",
        "---",
        "*Note générée à partir de données publiques (API Géo, OFGL) et du corpus documentaire. "
        "Elle doit être relue et validée par un chargé d'affaires.*",
    ]
    return "\n".join(lines)
