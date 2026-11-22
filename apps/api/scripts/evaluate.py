"""Phase 5 evaluation: generate answers, judge them with a local model, build the report.

Three steps, so a long run can be resumed and judged by several models:

  uv run python scripts/evaluate.py run baseline --top-k 2
  uv run python scripts/evaluate.py run chunks1200-k4 --top-k 4 \\
      --index-dir data/variants/chunks-1200/chroma
  uv run python scripts/evaluate.py run gemma-k2 --top-k 2 --model gemma3:4b
  uv run python scripts/evaluate.py judge gemma3:4b baseline chunks1200-k4 gemma-k2
  uv run python scripts/evaluate.py report baseline chunks1200-k4 gemma-k2

Results go to eval/results/<name>.jsonl (answers) and <name>.judge-<model>.jsonl (judgements).
"""

import argparse
import json
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import REPO_ROOT, settings  # noqa: E402
from providers import get_provider  # noqa: E402
from rag.answer import answer_question, build_messages  # noqa: E402
from rag.evaluation import (  # noqa: E402
    estimate_tokens,
    expected_pages,
    first_rank,
    has_keywords,
    percentile,
    rate,
)
from rag.retrieval import search  # noqa: E402

RESULTS = REPO_ROOT / "eval" / "results"

# Indicative cloud price (USD per million tokens, gpt-4o-mini class): check before quoting.
PRICE_INPUT, PRICE_OUTPUT = 0.15, 0.60

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {  # "reason" first: the model writes its justification before the verdicts
        "reason": {"type": "string"},
        "faithful": {"type": "boolean"},
        "correct": {"type": "boolean"},
    },
    "required": ["reason", "faithful", "correct"],
}
JUDGE_SYSTEM = (
    "Tu es un correcteur strict et factuel. On te donne une question, une réponse de référence, "
    "des extraits de documents et la réponse d'un assistant à noter. Réponds en JSON.\n"
    "- faithful : true seulement si CHAQUE affirmation de la réponse est appuyée par les extraits "
    "(aucun chiffre ni fait absent des extraits).\n"
    "- correct : true seulement si la réponse contient l'information de la réponse de référence, "
    "avec les mêmes chiffres, sans contradiction.\n"
    "reason : une phrase courte."
)


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")


def load_questions() -> list[dict]:
    lines = (REPO_ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


@contextmanager
def chat_model(name: str):
    """Temporarily point the Ollama provider at another chat model."""
    previous = settings.ollama_chat_model
    settings.ollama_chat_model = name
    try:
        yield
    finally:
        settings.ollama_chat_model = previous


def answer_with_trace(question: str, provider, top_k: int):
    """Answer a question and also return every passage retrieved (before the distance cut)."""
    retrieved = []

    def do_search(text: str):
        retrieved.extend(search(text, provider, k=top_k))
        return list(retrieved)

    return answer_question(question, provider, do_search), retrieved


def cmd_run(args: argparse.Namespace) -> None:
    if args.top_k:
        settings.top_k = args.top_k
    args.top_k = settings.top_k
    if args.model:
        settings.ollama_chat_model = args.model
    if args.index_dir:
        settings.vector_store_dir = REPO_ROOT / args.index_dir
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{args.name}.jsonl"
    done = {r["id"] for r in read_jsonl(path) if "id" in r}
    if not done:
        meta = {
            "_meta": {
                "name": args.name,
                "top_k": args.top_k,
                "chat_model": settings.ollama_chat_model,
                "embed_model": settings.ollama_embed_model,
                "index_dir": str(settings.vector_store_dir.relative_to(REPO_ROOT)),
                "max_distance": settings.max_distance,
                "date": time.strftime("%Y-%m-%d"),
            }
        }
        append_jsonl(path, meta)

    provider = get_provider()
    provider.warm_up()
    for q in load_questions():
        if q["id"] in done:
            continue
        started = time.time()
        answer, retrieved = answer_with_trace(q["question"], provider, args.top_k)
        latency = time.time() - started

        kept = [p for p in retrieved if p.distance <= settings.max_distance]
        prompt = "".join(m["content"] for m in build_messages(q["question"], kept)) if kept else ""
        row = {
            "id": q["id"],
            "type": q["type"],
            "category": q["category"],
            "refused": answer.refused,
            "text": answer.text,
            "sources": [
                {"source": p.source, "page": p.page, "text": p.text} for p in answer.sources
            ],
            "best_distance": round(retrieved[0].distance, 4) if retrieved else None,
            "latency_s": round(latency, 2),
            # No passage kept = the model was never called, so no tokens are spent.
            "prompt_tokens": estimate_tokens(prompt),
            "output_tokens": estimate_tokens(answer.text) if kept else 0,
        }
        if q["type"] == "answerable":
            expected = expected_pages(q)
            row["retrieval_rank"] = first_rank([(p.source, p.page) for p in retrieved], expected)
            cites_ok = any((s["source"], s["page"]) in expected for s in row["sources"])
            row["correct_rule"] = (
                not answer.refused and has_keywords(answer.text, q["keywords"]) and cites_ok
            )
        else:
            row["correct_rule"] = answer.refused  # a trap is handled well when refused
        append_jsonl(path, row)
        mark = "OK " if row["correct_rule"] else "KO "
        print(f"{mark}{q['id']:9} {latency:5.1f}s  {answer.text[:80]!r}", flush=True)


def judge_prompt(question: dict, row: dict) -> list[dict[str, str]]:
    excerpts = "\n\n".join(f"({s['source']}, p. {s['page']})\n{s['text']}" for s in row["sources"])
    user = (
        f"Question : {question['question']}\n\n"
        f"Réponse de référence : {question['expected_answer']}\n\n"
        f"Extraits cités :\n{excerpts}\n\n"
        f"Réponse de l'assistant à noter : {row['text']}"
    )
    return [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}]


def cmd_judge(args: argparse.Namespace) -> None:
    questions = {q["id"]: q for q in load_questions()}
    provider = get_provider()
    with chat_model(args.model):
        for name in args.names:
            out = RESULTS / f"{name}.judge-{slug(args.model)}.jsonl"
            done = {r["id"] for r in read_jsonl(out)}
            for row in read_jsonl(RESULTS / f"{name}.jsonl"):
                # Only real answers are judged; refusals and traps are scored by rule.
                if "id" not in row or row["id"] in done or row["refused"]:
                    continue
                if row["type"] != "answerable":
                    continue
                try:
                    verdict = json.loads(
                        provider.chat(judge_prompt(questions[row["id"]], row), JUDGE_SCHEMA)
                    )
                    result = {
                        "id": row["id"],
                        "faithful": bool(verdict["faithful"]),
                        "correct": bool(verdict["correct"]),
                        "reason": verdict["reason"],
                    }
                except (ValueError, KeyError) as error:
                    result = {
                        "id": row["id"],
                        "faithful": None,
                        "correct": None,
                        "reason": f"judge error: {error!r}",
                    }
                append_jsonl(out, result)
                print(
                    f"{name:18} {row['id']:9} "
                    f"faithful={result['faithful']} correct={result['correct']}",
                    flush=True,
                )


def fmt(count_total: tuple[int, int]) -> str:
    count, total = count_total
    return f"{count}/{total}" if total else "n/a"


def cmd_report(args: argparse.Namespace) -> None:
    judges = sorted(
        {
            p.name.split(".judge-")[1][:-6]
            for n in args.names
            for p in RESULTS.glob(f"{n}.judge-*.jsonl")
        }
    )
    header = [
        "Variante",
        "Bonnes (règle)",
        "Refus corrects",
        "Passage retrouvé",
        "Reform./fautes",
        "Médiane",
        "p95",
        "Tokens/q (ent.+sort.)",
        "Coût indicatif /1000 q",
    ]
    for j in judges:
        header += [f"Fidèle ({j})", f"Pertinente ({j})"]
    print("| " + " | ".join(header) + " |")
    print("|" + " --- |" * len(header))
    for name in args.names:
        rows = [r for r in read_jsonl(RESULTS / f"{name}.jsonl") if "id" in r]
        meta = next((r["_meta"] for r in read_jsonl(RESULTS / f"{name}.jsonl") if "_meta" in r), {})
        answerable = [r for r in rows if r["type"] == "answerable"]
        traps = [r for r in rows if r["type"] != "answerable"]
        varied = [r for r in answerable if r["category"] in ("paraphrase", "typo")]
        latencies = [r["latency_s"] for r in answerable if not r["refused"]]
        tokens_in = sum(r["prompt_tokens"] for r in rows)
        tokens_out = sum(r["output_tokens"] for r in rows)
        cost = (tokens_in * PRICE_INPUT + tokens_out * PRICE_OUTPUT) / 1e6 / len(rows) * 1000
        cells = [
            f"`{name}`",
            fmt(rate(r["correct_rule"] for r in answerable)),
            fmt(rate(r["correct_rule"] for r in traps)),
            fmt(rate(r["retrieval_rank"] is not None for r in answerable)),
            fmt(rate(r["correct_rule"] for r in varied)),
            f"{percentile(latencies, 0.5):.1f} s",
            f"{percentile(latencies, 0.95):.1f} s",
            f"{tokens_in // len(rows)} + {tokens_out // len(rows)}",
            f"{cost:.2f} $",
        ]
        for j in judges:
            verdicts = {v["id"]: v for v in read_jsonl(RESULTS / f"{name}.judge-{j}.jsonl")}
            judged = [verdicts[r["id"]] for r in answerable if r["id"] in verdicts]
            cells += [
                fmt(rate(v["faithful"] for v in judged)),
                fmt(rate(v["correct"] for v in judged)),
            ]
        print("| " + " | ".join(cells) + " |")
        print(f"<!-- {name}: {meta} -->", file=sys.stderr)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(required=True)

    run = sub.add_parser("run", help="answer every question with one configuration")
    run.add_argument("name")
    run.add_argument("--top-k", type=int, help="passages retrieved (default: settings)")
    run.add_argument("--model", help="Ollama chat model (default: settings)")
    run.add_argument(
        "--index-dir", help="Chroma folder relative to the repo (default: data/chroma)"
    )
    run.set_defaults(func=cmd_run)

    judge = sub.add_parser("judge", help="score saved answers with a local model")
    judge.add_argument("model")
    judge.add_argument("names", nargs="+")
    judge.set_defaults(func=cmd_judge)

    report = sub.add_parser("report", help="print the comparison table (Markdown)")
    report.add_argument("names", nargs="+")
    report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
