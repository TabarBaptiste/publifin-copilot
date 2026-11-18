import pytest

from agent.indicators import MissingData, compute_indicators
from agent.schemas import CommuneFinances


def finances(debt=60_000_000.0, savings=18_000_000.0, revenue=80_000_000.0, population=66_725):
    return CommuneFinances(
        year=2025,
        population=population,
        aggregates={
            "Encours de dette": debt,
            "Epargne brute": savings,
            "Recettes de fonctionnement": revenue,
        },
    )


def test_healthy_commune_has_no_alert():
    result = compute_indicators(finances(), requested_amount_eur=2_000_000)

    assert result.gross_savings_rate == pytest.approx(0.225)
    assert result.debt_years == pytest.approx(60 / 18)
    assert result.debt_years_after == pytest.approx(62 / 18)
    assert result.debt_per_capita_eur == pytest.approx(60_000_000 / 66_725)
    assert result.alerts == []


def test_low_savings_rate_raises_an_alert():
    result = compute_indicators(finances(savings=4_000_000.0), None)

    assert any("sous le seuil d'alerte de 7 %" in alert for alert in result.alerts)
    assert result.debt_years_after is None


def test_debt_above_twelve_years_raises_an_alert():
    result = compute_indicators(finances(debt=300_000_000.0), None)

    assert result.debt_years == pytest.approx(300 / 18)
    assert any("au-dessus du seuil de 12 ans" in alert for alert in result.alerts)


def test_request_that_would_cross_the_threshold_is_flagged():
    # 10.8 years today, 13.0 years if the 40 M EUR were fully borrowed.
    result = compute_indicators(finances(debt=194_400_000.0), requested_amount_eur=40_000_000)

    assert result.debt_years < 12 < result.debt_years_after
    assert any("porterait la capacité de désendettement" in alert for alert in result.alerts)


def test_negative_savings_means_no_debt_ratio():
    result = compute_indicators(finances(savings=-1_000_000.0), requested_amount_eur=1_000_000)

    assert result.debt_years is None and result.debt_years_after is None
    assert any("Épargne brute nulle ou négative" in alert for alert in result.alerts)


def test_missing_aggregate_is_reported():
    incomplete = CommuneFinances(year=2025, population=1000, aggregates={"Encours de dette": 1.0})

    with pytest.raises(MissingData, match="Epargne brute"):
        compute_indicators(incomplete, None)
