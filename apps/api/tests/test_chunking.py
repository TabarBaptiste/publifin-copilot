import pytest

from rag.chunking import split_text


def test_short_text_is_a_single_chunk():
    assert split_text("Bonjour le monde", size=100, overlap=10) == ["Bonjour le monde"]


def test_empty_text_gives_no_chunk():
    assert split_text("  \n ", size=100, overlap=10) == []


def test_chunks_respect_max_size_and_cover_the_text():
    words = [f"mot{i}" for i in range(500)]
    chunks = split_text(" ".join(words), size=200, overlap=40)

    assert len(chunks) > 1
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert chunks[0].startswith("mot0 ")
    assert chunks[-1].endswith("mot499")


def test_consecutive_chunks_overlap():
    words = [f"mot{i}" for i in range(500)]
    chunks = split_text(" ".join(words), size=200, overlap=40)

    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.split()[0] in previous.split()


def test_chunks_are_cut_on_word_boundaries():
    words = [f"mot{i}" for i in range(500)]
    valid = set(words)
    for chunk in split_text(" ".join(words), size=200, overlap=40):
        assert set(chunk.split()) <= valid


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        split_text("texte", size=10, overlap=10)
