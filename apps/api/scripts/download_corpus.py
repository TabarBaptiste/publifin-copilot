"""Download the public PDFs of the RAG corpus into data/corpus/ (not versioned).

Usage: uv run python scripts/download_corpus.py
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.sources import SOURCES  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"


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
