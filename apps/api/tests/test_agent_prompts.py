from agent.prompts import appreciation_messages
from agent.schemas import Commune, Indicators

COMMUNE = Commune(name="Quimper", insee="29232", department="29", population=63000)


def indicators(rate: float, years: float | None) -> Indicators:
    return Indicators(
        year=2024,
        population=63000,
        debt_outstanding_eur=1,
        debt_per_capita_eur=1,
        gross_savings_eur=1,
        gross_savings_rate=rate,
        debt_years=years,
        requested_amount_eur=None,
        debt_years_after=None,
        alerts=[],
    )


def facts(rate: float, years: float | None) -> str:
    return appreciation_messages(COMMUNE, indicators(rate, years), [], None, [])[1]["content"]


def test_the_code_states_each_comparison_with_its_threshold():
    healthy = facts(0.232, 3.2)
    assert "23,2 %, AU-DESSUS du seuil d'alerte de 7 % (pas d'alerte)" in healthy
    assert "3,2 ans, EN DEÇÀ du seuil d'alerte de 12 ans (pas d'alerte)" in healthy

    fragile = facts(0.05, 15.0)
    assert "5,0 %, SOUS le seuil d'alerte de 7 % (situation à surveiller)" in fragile
    assert "15,0 ans, AU-DELÀ du seuil d'alerte de 12 ans (situation à surveiller)" in fragile


def test_debt_years_may_be_unknown():
    assert "Capacité de désendettement : non calculable." in facts(-0.01, None)
