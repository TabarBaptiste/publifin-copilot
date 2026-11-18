from rag.evaluation import estimate_tokens, first_rank, has_keywords, percentile, rate


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
