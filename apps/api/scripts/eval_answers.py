"""Run the full question -> answer chain on eval/questions.jsonl and measure latency/quality.

Usage: uv run python scripts/eval_answers.py 5 3 2     (one run per top_k value)
"""

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import REPO_ROOT  # noqa: E402
from providers import get_provider  # noqa: E402
from rag.answer import answer_question  # noqa: E402
from rag.retrieval import search  # noqa: E402


def has_keywords(text: str, keywords: list[str]) -> bool:
    """Every keyword must appear (case-insensitive); "a|b" means a or b."""
    text = " ".join(text.lower().split())
    return all(any(alt in text for alt in kw.lower().split("|")) for kw in keywords)


def run(top_k: int) -> None:
    lines = (REPO_ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    questions = [json.loads(line) for line in lines if line.strip()]
    provider = get_provider()
    print(f"\n===== top_k={top_k} =====", flush=True)

    times, good_answers, good_refusals, n_answerable, n_refusable = [], 0, 0, 0, 0
    for q in questions:
        started = time.time()
        answer = answer_question(q["question"], provider, lambda s: search(s, provider, k=top_k))
        elapsed = time.time() - started
        if q["type"] == "answerable":
            n_answerable += 1
            times.append(elapsed)
            expected = {(s["source"], p) for s in q["expected_sources"] for p in s["pages"]}
            cites_ok = any((p.source, p.page) in expected for p in answer.sources)
            ok = not answer.refused and has_keywords(answer.text, q["keywords"]) and cites_ok
            good_answers += ok
            verdict = "OK " if ok else "KO "
        else:
            n_refusable += 1
            ok = answer.refused
            good_refusals += ok
            verdict = "OK " if ok else "KO "
        print(f"{verdict}{q['id']:9} {elapsed:5.1f}s  {answer.text[:100]!r}", flush=True)

    times.sort()
    p95 = times[min(len(times) - 1, int(0.95 * len(times)))]
    print(
        f"top_k={top_k}: bonnes réponses {good_answers}/{n_answerable} | "
        f"refus corrects {good_refusals}/{n_refusable} | "
        f"latence (questions à réponse) médiane {statistics.median(times):.1f}s, "
        f"moyenne {statistics.mean(times):.1f}s, p95 {p95:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    for k in [int(arg) for arg in sys.argv[1:]] or [5]:
        run(k)
