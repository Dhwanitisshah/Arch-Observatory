from app.services.metrics import analyze_file

SIMPLE_SOURCE = """
def add(a, b):
    return a + b
"""

BRANCHY_SOURCE = """
def classify(x):
    if x < 0:
        return "negative"
    elif x == 0:
        return "zero"
    elif x < 10:
        return "small"
    else:
        return "large"
"""

BROKEN_SOURCE = "def f(:\n  pass"


def test_simple_function():
    result = analyze_file(SIMPLE_SOURCE)

    assert result["parse_ok"] is True
    assert len(result["functions"]) == 1
    assert result["functions"][0]["complexity"] == 1
    assert result["functions"][0]["name"] == "add"


def test_branchy_function_complexity_matches_branches():
    result = analyze_file(BRANCHY_SOURCE)

    assert result["parse_ok"] is True
    assert len(result["functions"]) == 1
    # base complexity 1 + 3 elif/else branches with conditions (if/elif/elif) = 4
    assert result["functions"][0]["complexity"] == 4
    assert result["max_complexity"] == 4


def test_broken_source_does_not_raise():
    result = analyze_file(BROKEN_SOURCE)

    assert result["parse_ok"] is False
    assert result["functions"] == []
    assert result["max_complexity"] == 0
    assert "error" in result


def test_empty_string():
    result = analyze_file("")

    assert result["parse_ok"] is True
    assert result["functions"] == []
    assert result["max_complexity"] == 0
