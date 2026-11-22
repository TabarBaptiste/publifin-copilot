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


QUESTION_TYPES = {"answerable", "not_in_corpus", "off_topic"}
CATEGORIES = {"base", "paraphrase", "typo", "trap"}


def question_errors(questions: list[dict]) -> list[str]:
    """Problems in the question set (empty list = valid)."""
    errors = []
    ids = [q.get("id") for q in questions]
    errors += [f"duplicate id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    for q in questions:
        qid = q.get("id", "?")
        missing = {"id", "question", "type", "category", "expected_answer"} - q.keys()
        if missing:
            errors.append(f"{qid}: missing {sorted(missing)}")
            continue
        if q["type"] not in QUESTION_TYPES:
            errors.append(f"{qid}: unknown type {q['type']!r}")
        if q["category"] not in CATEGORIES:
            errors.append(f"{qid}: unknown category {q['category']!r}")
        answerable = q["type"] == "answerable"
        if answerable == (q["category"] == "trap"):
            errors.append(f"{qid}: category 'trap' must go with an unanswerable type")
        if answerable and not (q.get("keywords") and expected_pages(q)):
            errors.append(f"{qid}: an answerable question needs keywords and expected pages")
        if "variant_of" in q and q["variant_of"] not in ids:
            errors.append(f"{qid}: variant_of {q['variant_of']!r} does not exist")
    return errors


def quality_errors(questions: list[dict], rows: list[dict], min_answer_rate: float) -> list[str]:
    """Problems in saved evaluation results against the current question set."""
    by_id = {r["id"]: r for r in rows if "id" in r}
    missing = [q["id"] for q in questions if q["id"] not in by_id]
    if missing:
        return [f"results are stale: no result for {missing} (re-run scripts/evaluate.py)"]
    errors = []
    answerable = [by_id[q["id"]] for q in questions if q["type"] == "answerable"]
    good, total = rate(r["correct_rule"] for r in answerable)
    if good < min_answer_rate * total:
        errors.append(f"correct answers {good}/{total} below {min_answer_rate:.0%}")
    leaked = [
        q["id"] for q in questions if q["type"] != "answerable" and not by_id[q["id"]]["refused"]
    ]
    if leaked:
        errors.append(f"traps answered instead of refused: {leaked}")
    return errors
