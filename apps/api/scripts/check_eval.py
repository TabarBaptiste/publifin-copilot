"""CI gate for the evaluation (no LLM needed, the CI has no Ollama).

1. The question set is well formed.
2. The results committed for the current settings cover every question and stay above
   the quality bar. They are produced locally:
   uv run python scripts/evaluate.py run default-1200-k4

Usage: uv run python scripts/check_eval.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import REPO_ROOT, settings  # noqa: E402
from rag.evaluation import quality_errors, question_errors  # noqa: E402
from scripts.evaluate import load_questions, read_jsonl  # noqa: E402

RESULTS = REPO_ROOT / "eval" / "results" / "default-1200-k4.jsonl"
MIN_ANSWER_RATE = 0.75  # measured 30/38 (79 %) on 2026-11-22; traps must all be refused


def main() -> None:
    questions = load_questions()
    errors = question_errors(questions)
    if not errors:
        rows = read_jsonl(RESULTS)
        meta = next((r["_meta"] for r in rows if "_meta" in r), {})
        current = {
            "top_k": settings.top_k,
            "chat_model": settings.ollama_chat_model,
            "max_distance": settings.max_distance,
        }
        stale = {k: (meta.get(k), v) for k, v in current.items() if meta.get(k) != v}
        if stale:
            errors.append(f"results were measured with other settings (saved, current): {stale}")
        errors += quality_errors(questions, rows, MIN_ANSWER_RATE)
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        sys.exit(1)
    print(f"OK: {len(questions)} questions, results in {RESULTS.name} above the bar")


if __name__ == "__main__":
    main()
