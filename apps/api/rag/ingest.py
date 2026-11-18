"""Ingest the PDFs of data/corpus into the vector store selected by the configuration.

Usage: uv run python -m rag.ingest
"""

import time

from config import settings
from providers import get_provider
from rag.chunking import chunk_pdf
from rag.vector_store import get_store

BATCH_SIZE = 16


def main() -> None:
    pdfs = sorted(settings.corpus_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF in {settings.corpus_dir}: run scripts/download_corpus.py first.")

    provider = get_provider()
    store = get_store()
    # Rebuild from scratch so the store always matches the corpus folder.
    store.reset()

    for pdf in pdfs:
        chunks = chunk_pdf(pdf, settings.chunk_size, settings.chunk_overlap)
        started = time.time()
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            store.add(batch, provider.embed([c.text for c in batch]))
        print(f"{pdf.name}: {len(chunks)} chunks in {time.time() - started:.0f}s", flush=True)

    print(f"Done: {store.count()} chunks ({type(store).__name__})")


if __name__ == "__main__":
    main()
