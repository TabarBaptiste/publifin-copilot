"""Measure retrieval quality on eval/questions.jsonl (no LLM call).

Usage: uv run python scripts/eval_retrieval.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import REPO_ROOT, settings  # noqa: E402
from providers import get_provider  # noqa: E402
from rag.retrieval import search  # noqa: E402

THRESHOLDS = [0.35, 0.40, 0.45, 0.50, 0.55]


def main() -> None:
    lines = (REPO_ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    questions = [json.loads(line) for line in lines if line.strip()]
    provider = get_provider()

    answerable_best: list[float] = []  # distance of the best passage, per answerable question
    others_best: list[float] = []  # same for questions that must be refused
    hits = {1: 0, 3: 0, 5: 0}
    n_answerable = 0

    for q in questions:
        passages = search(q["question"], provider, k=5)
        best = passages[0].distance
        if q["type"] != "answerable":
            others_best.append(best)
            print(f"{q['id']:9} best={best:.3f}  (doit être refusée)")
            continue
        n_answerable += 1
        expected = {(s["source"], p) for s in q["expected_sources"] for p in s["pages"]}
        rank = next(
            (i for i, p in enumerate(passages, start=1) if (p.source, p.page) in expected), None
        )
        for k in hits:
            hits[k] += rank is not None and rank <= k
        answerable_best.append(best)
        print(f"{q['id']:9} best={best:.3f}  bon passage au rang {rank or 'absent'}")

    print(
        f"\nPassage attendu retrouvé : top1 {hits[1]}/{n_answerable}, "
        f"top3 {hits[3]}/{n_answerable}, top5 {hits[5]}/{n_answerable}"
    )
    print(
        f"Distance du meilleur passage : réponses possibles max={max(answerable_best):.3f} ; "
        f"à refuser min={min(others_best):.3f}"
    )
    print(f"\nSeuil actuel : {settings.max_distance}")
    for t in THRESHOLDS:
        kept = sum(d <= t for d in answerable_best)
        refused = sum(d > t for d in others_best)
        print(
            f"  seuil {t:.2f} : {kept}/{len(answerable_best)} questions à réponse gardées, "
            f"{refused}/{len(others_best)} refus corrects"
        )


if __name__ == "__main__":
    main()
