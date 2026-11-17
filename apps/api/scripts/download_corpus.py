"""Download the public PDFs of the RAG corpus into data/corpus/ (not versioned).

Usage: uv run python scripts/download_corpus.py
"""

import urllib.request
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"

SOURCES = {
    "rgpd-reglement-2016-679.pdf": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32016R0679",
    "ai-act-reglement-2024-1689.pdf": "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=OJ:L_202401689",
    "cnil-ia-liste-de-verification-2025.pdf": "https://www.cnil.fr/sites/default/files/2025-07/ia_liste_de_verification.pdf",
    "cour-des-comptes-finances-locales-2026.pdf": "https://www.ccomptes.fr/sites/default/files/2026-07/20260709-Finances-publiques-locales-2026.pdf",
    "ofgl-rapport-2025-vue-d-ensemble.pdf": "https://www.collectivites-locales.gouv.fr/files/files/Etudes-et-statistiques/OFGL/rapport%202025/Rapport%20OFGL%202025%201%20vue%20d%20ensemble.pdf",
    "dgcl-cl-en-chiffres-2025-ch1-synthese.pdf": "https://www.collectivites-locales.gouv.fr/files/files/Etudes-et-statistiques/Les%20collectivit%C3%A9s%20locales%20en%20chiffres/Les%20collectivit%C3%A9s%20en%20chiffres/2025/Chapitre%201%20-%20Synth%C3%A8se.pdf",
}


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        target = CORPUS_DIR / name
        if target.exists():
            print(f"skip   {name}")
            continue
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=120) as response:
            target.write_bytes(response.read())
        print(f"saved  {name} ({target.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
