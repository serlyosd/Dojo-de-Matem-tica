from __future__ import annotations

import re
import unicodedata


ANALYZER_VERSION = "python-deterministic-v1"

NUMBER_WORDS = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _numbers(text: str) -> list[int]:
    plain = _plain(text)
    values = [int(value) for value in re.findall(r"(?<![\d.,])\d+(?![\d.,])", plain)]
    values.extend(NUMBER_WORDS[word] for word in re.findall(r"[a-z]+", plain) if word in NUMBER_WORDS)
    return values


def analyze_basic_answer(answer: str) -> str:
    """Confere deterministicamente a resposta da única missão da fase 1."""
    cleaned = " ".join(answer.split())
    plain = _plain(cleaned)
    numbers = _numbers(cleaned)
    division_shown = any(marker in plain for marker in ("/", "÷", "divid"))
    has_expected_expression = 24 in numbers and 6 in numbers and division_shown
    has_correct_result = 4 in numbers

    understood = f'Entendi a resposta confirmada como: “{cleaned}”.'
    if has_correct_result:
        check = "Conferência local: 24 ÷ 6 = 4. A quantidade final de 4 veículos está correta."
        question = (
            "Como você conferiu que os 4 veículos usam todas as 24 peças?"
            if has_expected_expression
            else "Que conta você usou para chegar a 4 veículos?"
        )
    elif numbers:
        check = "Conferência local: 24 ÷ 6 = 4. A quantidade final informada ainda não corresponde a 4 veículos."
        question = "Você pode separar as 24 peças em grupos de 6 e contar os grupos?"
    else:
        check = "Não encontrei uma quantidade final clara para conferir. A conta de referência é 24 ÷ 6."
        question = "Quantos grupos completos de 6 você formou?"

    return "\n\n".join((understood, check, question))

