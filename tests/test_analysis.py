from app.analysis import ANALYZER_VERSION, analyze_basic_answer, evaluate_basic_answer


def test_correct_answer_finishes_mission():
    result = analyze_basic_answer("24 dividido por 6 = 4")
    assert "quantidade final de 4 veículos está correta" in result
    assert "Missão concluída" in result
    assert evaluate_basic_answer("Quatro veículos").correct
    assert ANALYZER_VERSION == "python-deterministic-v1"


def test_first_error_identifies_type_and_requests_new_calculation():
    result = analyze_basic_answer("Montei 3 veículos", wrong_attempt=1)
    assert "Tipo de erro: resultado incorreto" in result
    assert "nova conta" in result


def test_second_error_gives_concrete_hint():
    result = analyze_basic_answer("Montei 3 veículos", wrong_attempt=2)
    assert "Dica:" in result
    assert "grupos de 6" in result


def test_third_error_shows_solution_and_stops_loop():
    result = analyze_basic_answer("Montei 3 veículos", wrong_attempt=3)
    assert "Resolução:" in result
    assert "24 ÷ 6" in result
    assert "encerrar ou iniciar uma nova missão" in result
    assert analyze_basic_answer("3", wrong_attempt=99) == result.replace("Montei 3 veículos", "3")


def test_answer_without_number_identifies_missing_quantity():
    result = analyze_basic_answer("Eu separei as peças", wrong_attempt=1)
    assert "resposta sem quantidade final" in result
