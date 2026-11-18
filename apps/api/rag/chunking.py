from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# ~4 characters per token for French text: 2400 chars ≈ 600 tokens, 300 chars ≈ 75 tokens.
CHUNK_SIZE = 2400
CHUNK_OVERLAP = 300


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str  # file name
    page: int  # 1-based
    index: int  # position of the chunk within the page


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks of at most `size` characters, cut on whitespace, with overlap."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    text = " ".join(text.split())
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start + size - overlap, end)
            if cut > start:
                end = cut
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        # Next chunk starts at the first word boundary inside the overlap zone.
        boundary = text.find(" ", max(end - overlap, start + 1), end)
        start = boundary + 1 if boundary != -1 else end
    return [chunk for chunk in chunks if chunk]


def chunk_pdf(path: Path, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[Chunk]:
    """Read a PDF page by page and return its chunks, keeping file name and page number."""
    chunks: list[Chunk] = []
    for page_number, page in enumerate(PdfReader(path).pages, start=1):
        for index, text in enumerate(split_text(page.extract_text() or "", size, overlap)):
            chunks.append(Chunk(text=text, source=path.name, page=page_number, index=index))
    return chunks
