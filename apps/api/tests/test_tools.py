import httpx
import pytest
from pydantic import ValidationError

from agent.tools import FinancesInput, GeoLookupInput, PublicDataTools, ToolError


def tools_with(handler):
    return PublicDataTools(httpx.Client(transport=httpx.MockTransport(handler)))


def test_find_commune_prefers_the_most_populated_exact_match():
    def handler(request):
        assert request.url.params["nom"] == "Saint-Denis"
        return httpx.Response(
            200,
            json=[
                {
                    "nom": "Saint-Denis",
                    "code": "93066",
                    "population": 150000,
                    "departement": {"code": "93", "nom": "Seine-Saint-Denis"},
                },
                {
                    "nom": "Saint-Denis",
                    "code": "97411",
                    "population": 150500,
                    "departement": {"code": "974", "nom": "La Réunion"},
                },
                {
                    "nom": "Saint-Denis-lès-Bourg",
                    "code": "01344",
                    "population": 5000,
                    "departement": {"code": "01", "nom": "Ain"},
                },
            ],
        )

    commune = tools_with(handler).find_commune(GeoLookupInput(name="Saint-Denis"))

    assert (commune.insee, commune.homonyms) == ("97411", 1)


def test_find_commune_ignores_accents_and_hyphens():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {
                    "nom": "Fort-de-France",
                    "code": "97209",
                    "population": 77000,
                    "departement": {"code": "972", "nom": "Martinique"},
                }
            ],
        )

    commune = tools_with(handler).find_commune(GeoLookupInput(name="fort de france"))

    assert commune.insee == "97209"


def test_find_commune_unknown_name_is_a_tool_error():
    tools = tools_with(lambda request: httpx.Response(200, json=[]))

    with pytest.raises(ToolError, match="introuvable"):
        tools.find_commune(GeoLookupInput(name="Xyzzyville"))


def test_unreachable_service_is_a_tool_error():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(ToolError, match="indisponible"):
        tools_with(handler).find_commune(GeoLookupInput(name="Quimper"))


def test_get_finances_uses_latest_year_and_main_budget():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        if request.url.params["select"] == "exer":
            return httpx.Response(200, json={"results": [{"exer": "2025-01-01T00:00:00+00:00"}]})
        return httpx.Response(
            200,
            json={
                "results": [
                    {"agregat": "Encours de dette", "montant": 59701543.0, "ptot": 66725},
                    {"agregat": "Epargne brute", "montant": 18422833.0, "ptot": 66725},
                ]
            },
        )

    result = tools_with(handler).get_finances(FinancesInput(insee="29232"))

    assert result.year == 2025 and result.population == 66725
    assert result.aggregates["Epargne brute"] == 18422833.0
    assert 'type_de_budget="Budget principal"' in calls[1]["where"]
    assert "year(exer)=2025" in calls[1]["where"]


def test_inputs_are_strictly_validated():
    with pytest.raises(ValidationError):
        FinancesInput(insee='29232" OR 1=1')
    with pytest.raises(ValidationError):
        GeoLookupInput(name="Quimper", department="29; DROP")
    with pytest.raises(ValidationError):
        GeoLookupInput(name="Quimper", unexpected="x")
