from app.ai.answer_service import build_answer


def test_count_answer():
    assert build_answer("How many employees are there?", ["count"], [[450]], False) == "There are 450 employees."


def test_empty():
    assert "No matching" in build_answer("x", ["a"], [], False)


def test_top_n():
    rows = [[i, i] for i in range(5)]
    assert build_answer("Show the top 5 customers by spending", ["n", "v"], rows, False) == "Here are the top 5 results."
