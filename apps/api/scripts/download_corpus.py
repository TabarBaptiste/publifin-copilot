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
