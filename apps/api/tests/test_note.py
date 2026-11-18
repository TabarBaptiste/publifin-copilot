from agent.indicators import compute_indicators
from agent.note import build_note, fr_eur
from agent.schemas import Commune, CommuneFinances, ExtractedRequest
from rag.retrieval import Passage


def indicators(debt=51_400_000.0, savings=4_700_000.0, revenue=65_000_000.0, amount=40_000_000):
    finances = CommuneFinances(
        year=2025,
        population=48041,
        aggregates={
            "Encours de dette": debt,
            "Epargne brute": savings,
            "Recettes de fonctionnement": revenue,
        },
    )
    return compute_indicators(finances, amount)


BASTIA = Commune(name="Bastia", insee="2B033", department="Haute-Corse", population=46867)
REQUEST = ExtractedRequest(
    commune_name="Bastia", amount_eur=40_000_000, purpose="rénovation du port"
)


def test_amounts_are_formatted_in_french():
    assert fr_eur(40_000_000) == "40,0 M€"
    assert fr_eur(350_000) == "350 000 €"
    assert fr_eur(None) == "non précisé"


def test_note_has_figures_alerts_and_numbered_sources():
    passages = [Passage("t", "cour-des-comptes-finances-locales-2026.pdf", 57, 0.2)]

    note = build_note(BASTIA, REQUEST, indicators(), "Commentaire [1].", passages)

    assert "# Pré-analyse : Bastia (Haute-Corse)" in note
    assert "**Demande** : 40,0 M€ — rénovation du port" in note
    assert "- Population : 48 041 habitants" in note
    assert "10,9 ans" in note and "au-dessus du seuil de 12 ans" in note
    assert "Commentaire [1]." in note
    # one bullet per source, so Markdown does not merge them on a single line
    assert "- [1] Cour des comptes — Finances publiques locales (2026), page 57" in note
    assert "relue et validée par un chargé d'affaires" in note


def test_note_without_sources_has_no_sources_section():
    note = build_note(BASTIA, REQUEST, indicators(), "Aucun commentaire.", [])

    assert "## Sources documentaires" not in note


def test_homonyms_are_flagged_for_the_reviewer():
    commune = BASTIA.model_copy(update={"homonyms": 2})

    note = build_note(commune, REQUEST, indicators(), "x", [])

    assert "2 autre(s) commune(s) portent le même nom" in note
