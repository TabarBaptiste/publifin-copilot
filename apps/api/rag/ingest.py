"""Ingest the PDFs of data/corpus into the local vector store.

Usage: uv run python -m rag.ingest
"""

import time

import chromadb

from config import settings
from providers.ollama import embed
from rag.chunking import chunk_pdf

COLLECTION = "corpus"
BATCH_SIZE = 16


def main() -> None:
    pdfs = sorted(settings.corpus_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDF in {settings.corpus_dir}: run scripts/download_corpus.py first.")

    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    # Rebuild from scratch so the store always matches the corpus folder.
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    for pdf in pdfs:
        chunks = chunk_pdf(pdf)
        started = time.time()
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            collection.add(
                ids=[f"{c.source}:{c.page}:{c.index}" for c in batch],
                documents=[c.text for c in batch],
                embeddings=embed([c.text for c in batch]),
                metadatas=[{"source": c.source, "page": c.page} for c in batch],
            )
        print(f"{pdf.name}: {len(chunks)} chunks in {time.time() - started:.0f}s", flush=True)

    print(f"Done: {collection.count()} chunks in {settings.vector_store_dir}")


if __name__ == "__main__":
    main()
