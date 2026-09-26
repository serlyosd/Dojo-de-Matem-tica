from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


ANALYZER_VERSION = "python-deterministic-v1"


@dataclass(frozen=True)
class AnswerEvaluation:
    correct: bool
    error_type: str | None
    understood: str

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


def evaluate_basic_answer(answer: str) -> AnswerEvaluation:
    cleaned = " ".join(answer.split())
    numbers = _numbers(cleaned)
    has_correct_result = 4 in numbers

    understood = f'Entendi a resposta confirmada como: “{cleaned}”.'
    if has_correct_result:
        return AnswerEvaluation(True, None, understood)
    return AnswerEvaluation(False, "resultado incorreto" if numbers else "resposta sem quantidade final", understood)


def analyze_basic_answer(answer: str, wrong_attempt: int = 1) -> str:
    """Confere a missão e encerra o reforço após no máximo três erros."""
    evaluation = evaluate_basic_answer(answer)
    if evaluation.correct:
        return "\n\n".join((
            evaluation.understood,
            "Conferência local: 24 ÷ 6 = 4. A quantidade final de 4 veículos está correta.",
            "Missão concluída. Você pode encerrar ou iniciar uma nova missão.",
        ))

    attempt = min(max(wrong_attempt, 1), 3)
    if attempt == 1:
        guidance = f"Tipo de erro: {evaluation.error_type}. Faça uma nova conta e tente novamente."
    elif attempt == 2:
        guidance = "Dica: desenhe 24 peças e forme grupos de 6. Depois conte quantos grupos completos aparecem."
    else:
        guidance = (
            "Resolução: 1) temos 24 peças; 2) cada veículo usa 6; "
            "3) calculamos 24 ÷ 6; 4) o resultado é 4 veículos. "
            "Você pode encerrar ou iniciar uma nova missão."
        )

    return "\n\n".join((evaluation.understood, guidance))
