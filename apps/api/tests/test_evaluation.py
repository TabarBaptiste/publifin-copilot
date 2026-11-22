from rag.evaluation import (
    estimate_tokens,
    first_rank,
    has_keywords,
    percentile,
    quality_errors,
    question_errors,
    rate,
)


def test_keywords_are_case_and_whitespace_insensitive():
    assert has_keywords("Jusqu'à  20 000 000   EUR\nou 4 %", ["20 000 000", "4 %"])


def test_keyword_alternatives_accept_either_form():
    assert has_keywords("au bout de douze ans", ["douze|12"])
    assert not has_keywords("au bout de dix ans", ["douze|12"])


def test_all_keywords_are_required():
    assert not has_keywords("35 000 000 EUR", ["35 000 000", "7 %"])


def test_first_rank_is_one_based_and_none_when_absent():
    expected = {("a.pdf", 3)}
    assert first_rank([("a.pdf", 1), ("a.pdf", 3)], expected) == 2
    assert first_rank([("a.pdf", 1)], expected) is None


def test_percentile_uses_nearest_rank():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    assert percentile(values, 0.5) == 5.0
    assert percentile(values, 0.95) == 10.0
    assert percentile([], 0.5) == 0.0


def test_rate_ignores_unevaluated_items():
    assert rate([True, False, None, True]) == (2, 3)


def test_estimate_tokens_rounds_up():
    assert estimate_tokens("a" * 7) == 2


def make_question(qid, qtype="answerable", **extra):
    base = {"id": qid, "question": "?", "type": qtype, "expected_answer": "x"}
    if qtype == "answerable":
        base |= {"category": "base", "keywords": ["x"]}
        base["expected_sources"] = [{"source": "a.pdf", "pages": [1]}]
    else:
        base |= {"category": "trap", "keywords": [], "expected_sources": []}
    return base | extra


def test_valid_question_set_has_no_error():
    questions = [
        make_question("q1"),
        make_question("q1b", variant_of="q1"),
        make_question("t", "off_topic"),
    ]
    assert question_errors(questions) == []


def test_question_set_errors_are_reported():
    questions = [
        make_question("q1"),
        make_question("q1"),
        make_question("q2", keywords=[]),
        make_question("q3", variant_of="nope"),
        make_question("t", "off_topic", category="base"),
    ]
    errors = " | ".join(question_errors(questions))
    assert "duplicate id q1" in errors
    assert "q2: an answerable question needs" in errors
    assert "q3: variant_of 'nope'" in errors
    assert "t: category 'trap'" in errors


def test_quality_gate_flags_low_rate_and_leaked_traps():
    questions = [make_question("q1"), make_question("q2"), make_question("t", "off_topic")]
    rows = [
        {"id": "q1", "correct_rule": True, "refused": False},
        {"id": "q2", "correct_rule": False, "refused": True},
        {"id": "t", "correct_rule": False, "refused": False},
    ]
    errors = " | ".join(quality_errors(questions, rows, 0.75))
    assert "correct answers 1/2 below 75%" in errors
    assert "traps answered instead of refused: ['t']" in errors
    assert quality_errors(questions, rows[:1] + rows[2:], 0.5)[0].startswith("results are stale")
