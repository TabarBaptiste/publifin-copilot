"""Financial indicators computed from public data. Pure functions: no I/O, easy to test."""

from agent.schemas import CommuneFinances, Indicators

# Alert thresholds quoted by the Cour des comptes ("Les finances publiques locales", 2026):
# gross savings below 7 % of operating revenue (p. 57), debt above 12 years of savings (p. 87).
GROSS_SAVINGS_RATE_ALERT = 0.07
DEBT_YEARS_ALERT = 12.0

REQUIRED_AGGREGATES = ("Encours de dette", "Epargne brute", "Recettes de fonctionnement")


def fr(value: float, decimals: int = 1) -> str:
    """French number format: decimal comma."""
    return f"{value:.{decimals}f}".replace(".", ",")


class MissingData(Exception):
    """The public data lacks an aggregate needed for the analysis."""


def compute_indicators(finances: CommuneFinances, requested_amount_eur: float | None) -> Indicators:
    missing = [name for name in REQUIRED_AGGREGATES if name not in finances.aggregates]
    if missing:
        raise MissingData(f"Agrégats absents des données publiques : {', '.join(missing)}")

    debt = finances.aggregates["Encours de dette"]
    savings = finances.aggregates["Epargne brute"]
    revenue = finances.aggregates["Recettes de fonctionnement"]
    if revenue <= 0 or finances.population <= 0:
        raise MissingData("Recettes de fonctionnement ou population nulles : calcul impossible")

    savings_rate = savings / revenue
    debt_years = debt / savings if savings > 0 else None
    debt_years_after = (
        (debt + requested_amount_eur) / savings
        if savings > 0 and requested_amount_eur is not None
        else None
    )

    alerts: list[str] = []
    if savings_rate < GROSS_SAVINGS_RATE_ALERT:
        alerts.append(
            f"Taux d'épargne brute de {fr(savings_rate * 100)} %, sous le seuil d'alerte de "
            f"{fr(GROSS_SAVINGS_RATE_ALERT * 100, 0)} %."
        )
    if savings <= 0:
        alerts.append("Épargne brute nulle ou négative : la dette ne peut pas être remboursée.")
    elif debt_years is not None and debt_years > DEBT_YEARS_ALERT:
        alerts.append(
            f"Capacité de désendettement de {fr(debt_years)} ans, au-dessus du seuil de "
            f"{fr(DEBT_YEARS_ALERT, 0)} ans."
        )
    if debt_years_after is not None and debt_years_after > DEBT_YEARS_ALERT >= (debt_years or 0):
        alerts.append(
            f"Emprunter la totalité du montant demandé porterait la capacité de désendettement à "
            f"{fr(debt_years_after)} ans, au-dessus du seuil de {fr(DEBT_YEARS_ALERT, 0)} ans."
        )

    return Indicators(
        year=finances.year,
        population=finances.population,
        debt_outstanding_eur=debt,
        debt_per_capita_eur=debt / finances.population,
        gross_savings_eur=savings,
        gross_savings_rate=savings_rate,
        debt_years=debt_years,
        requested_amount_eur=requested_amount_eur,
        debt_years_after=debt_years_after,
        alerts=alerts,
    )
