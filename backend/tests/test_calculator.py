from app.tools.calculator import calculate


def test_addition():
    assert calculate("2 + 3") == "5"


def test_subtraction():
    assert calculate("10 - 4") == "6"


def test_multiplication():
    assert calculate("6 * 7") == "42"


def test_division():
    assert calculate("15 / 3") == "5.0"


def test_complex_expression():
    assert calculate("(2 + 3) * 4") == "20"


def test_power():
    assert calculate("2 ** 3") == "8"


def test_invalid_expression():
    result = calculate("hello")
    assert "Error" in result
