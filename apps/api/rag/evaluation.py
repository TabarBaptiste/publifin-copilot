"""Pure helpers shared by the evaluation scripts (no I/O, no LLM call)."""

import math
from collections.abc import Iterable, Sequence

CHARS_PER_TOKEN = 3.5  # same rough estimate as the agent's token budget


def has_keywords(text: str, keywords: list[str]) -> bool:
    """Every keyword must appear (case-insensitive); "a|b" means a or b."""
    text = " ".join(text.lower().split())
    return all(any(alt in text for alt in kw.lower().split("|")) for kw in keywords)


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def expected_pages(question: dict) -> set[tuple[str, int]]:
    return {(s["source"], p) for s in question["expected_sources"] for p in s["pages"]}


def first_rank(found: Sequence[tuple[str, int]], expected: set[tuple[str, int]]) -> int | None:
    """1-based rank of the first retrieved (source, page) that is expected, or None."""
    return next((i for i, key in enumerate(found, start=1) if key in expected), None)


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile (q between 0 and 1); 0.0 for an empty list."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1)]


def rate(flags: Iterable[bool | None]) -> tuple[int, int]:
    """(true count, evaluated count); None means "not evaluated" and is ignored."""
    evaluated = [f for f in flags if f is not None]
    return sum(evaluated), len(evaluated)
