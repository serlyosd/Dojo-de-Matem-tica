from app.analysis import ANALYZER_VERSION, analyze_basic_answer


def test_correct_answer_with_calculation():
    result = analyze_basic_answer("24 dividido por 6 = 4")
    assert "quantidade final de 4 veículos está correta" in result
    assert "Como você conferiu" in result
    assert ANALYZER_VERSION == "python-deterministic-v1"


def test_correct_answer_without_calculation_asks_for_operation():
    result = analyze_basic_answer("Quatro veículos")
    assert "está correta" in result
    assert "Que conta você usou" in result


def test_incorrect_numeric_answer_is_deterministic():
    result = analyze_basic_answer("Montei 3 veículos")
    assert "ainda não corresponde a 4 veículos" in result


def test_answer_without_number_requests_clear_quantity():
    result = analyze_basic_answer("Eu separei as peças")
    assert "Não encontrei uma quantidade final clara" in result

