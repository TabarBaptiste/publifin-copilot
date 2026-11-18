import pytest

from agent.amounts import parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("La commune de Quimper demande 2 M€ pour rénover son école.", 2_000_000),
        ("demande 2M€", 2_000_000),
        ("un prêt de 2,5 millions d'euros", 2_500_000),
        ("un prêt de 2.5 millions d’euros", 2_500_000),
        ("une enveloppe de 350 k€", 350_000),
        ("une enveloppe de 350 K€", 350_000),
        ("une enveloppe de 750 milliers d'euros", 750_000),
        ("montant : 350 000 €", 350_000),
        ("montant : 350 000 euros", 350_000),
        ("montant : 1 200 000 €", 1_200_000),
        ("montant : 1 200 000 €", 1_200_000),
    ],
)
def test_amounts_in_french_notations(text, expected):
    assert parse_amount(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["Quimper demande un financement", "ouverte depuis 2 ans", ""])
def test_no_amount_gives_none(text):
    assert parse_amount(text) is None
