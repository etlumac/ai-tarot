from __future__ import annotations

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


# Пороги
INAPPROPRIATE_HARD_THRESHOLD: float = 0.85
TOXICITY_THRESHOLD: float = 0.75


_inappropriate_pipe = None
_toxicity_pipe = None


def _get_inappropriate_pipe():
    global _inappropriate_pipe
    if _inappropriate_pipe is None:
        from transformers import pipeline
        import torch

        logger.info("Loading apanc/russian-inappropriate-messages...")
        device = 0 if torch.cuda.is_available() else -1
        _inappropriate_pipe = pipeline(
            "text-classification",
            model="apanc/russian-inappropriate-messages",
            device=device,
            truncation=True,
            max_length=128,
        )
        logger.info("russian-inappropriate-messages loaded")
    return _inappropriate_pipe


def _get_toxicity_pipe():
    global _toxicity_pipe
    if _toxicity_pipe is None:
        from transformers import pipeline
        import torch

        logger.info("Loading s-nlp/russian_toxicity_classifier...")
        device = 0 if torch.cuda.is_available() else -1
        _toxicity_pipe = pipeline(
            "text-classification",
            model="s-nlp/russian_toxicity_classifier",
            device=device,
            truncation=True,
            max_length=128,
        )
        logger.info("russian_toxicity_classifier loaded")
    return _toxicity_pipe



# Типы результатов
class InappropriateResult(NamedTuple):
    p_inappropriate: float  # вероятность inappropriate [0..1]
    is_blocked: bool        # True если p >= INAPPROPRIATE_HARD_THRESHOLD


class ToxicityResult(NamedTuple):
    score: float      # confidence модели
    is_toxic: bool    # True если label=toxic И score >= TOXICITY_THRESHOLD


# Публичные функции
def check_inappropriate(text: str) -> InappropriateResult:
    """
    Прогоняет текст через apanc/russian-inappropriate-messages.
    Возвращает вероятность inappropriate и флаг блокировки.
    """
    pipe = _get_inappropriate_pipe()
    result = pipe(text)[0]

    label: str = result["label"]
    score: float = result["score"]

    p_inappropriate = score if label == "LABEL_1" else 1.0 - score

    return InappropriateResult(
        p_inappropriate=p_inappropriate,
        is_blocked=p_inappropriate >= INAPPROPRIATE_HARD_THRESHOLD,
    )


def check_toxicity(text: str) -> ToxicityResult:
    """
    Прогоняет текст через s-nlp/russian_toxicity_classifier.
    Возвращает score и флаг is_toxic.
    """
    pipe = _get_toxicity_pipe()
    result = pipe(text)[0]

    label: str = result["label"]
    score: float = result["score"]

    return ToxicityResult(
        score=score,
        is_toxic=label == "toxic" and score >= TOXICITY_THRESHOLD,
    )