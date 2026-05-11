"""
router.py — Главный оркестратор Safety Router.

Этот файл содержит бизнес-логику маршрутизации: в каком порядке
вызывать уровни, что делать с каждым результатом, какое решение вернуть.
Сами паттерны живут в rules.py, сами модели — в models.py.

Что здесь есть:
RouterDecision (enum)
    Три возможных исхода:
    · BLOCKED — фиксированный текст-заглушка, Grok не вызывается.
    · TOXIC_SAFE — бытовая грубость и раздражение. Идёт в Theme Classifier
    · SAFE — обычный вопрос. Идёт в Theme Classifier.

RouterResult (dataclass)
    Результат одного вызова route().
    Поля: decision, category (для логов), source (какой уровень
    сработал), score (confidence ML-модели или None для правил).
    Свойство goes_to_classifier — True для SAFE и TOXIC_SAFE,
    единственная проверка которую нужно делать в prediction_service.

route(text) — основная функция.
    Запускает четыре уровня по порядку, возвращает первый сработавший.

    Уровень 1 (~1 мс):   Идиомы → SAFE (байпас всего, включая s-nlp).
                          Regex BLOCK_PATTERNS → BLOCKED.
    Уровень 2 (~40 мс):  inappropriate-модель, только если p >= 0.85 → BLOCKED.
    Уровень 3a (~0 мс):  Словарь раздражения → TOXIC_SAFE.
    Уровень 3b (~0 мс):  Идиомы повторно (перед s-nlp) → SAFE.
    Уровень 4 (~30 мс):  s-nlp toxicity → TOXIC_SAFE.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .rules import (
    BLOCK_PATTERNS,
    DEATH_ALLOWLIST,
    is_idiom,
    is_mild_frustration,
    match_any,
)
from .models import check_inappropriate, check_toxicity



# Возможные решения
class RouterDecision(str, Enum):
    BLOCKED    = "blocked"     # фиксированный ответ, Grok не вызывается
    TOXIC_SAFE = "toxic_safe"  # идёт в классификатор
    SAFE       = "safe"        # идёт в классификатор



# Результат роутера
@dataclass(frozen=True)
class RouterResult:
    decision: RouterDecision
    category: str | None  # категория срабатывания
    source: str           # уровень: rules / inappropriate_model / frustration_dict /
                          #          toxicity_model / idiom_bypass / passed_all
    score: float | None   # confidence ML-модели (None для правил и словарей)


    @property
    def goes_to_classifier(self) -> bool:
        """True для SAFE и TOXIC_SAFE — оба идут в Theme Classifier."""
        return self.decision in (RouterDecision.SAFE, RouterDecision.TOXIC_SAFE)

    @property
    def is_toxic_safe(self) -> bool:
        """True если вопрос груб/раздражителен, но допустим для таролога."""
        return self.decision == RouterDecision.TOXIC_SAFE

    @property
    def is_self_harm(self) -> bool:
        """True если это суицидальный/самоповреждающий контент."""
        return self.category == "self_harm"


# Тексты-заглушки при BLOCKED
_SELF_HARM_RESPONSE = (
    "Слышу, что тебе сейчас очень тяжело. Карты Таро здесь не помогут — "
    "пожалуйста, позвони на горячую линию психологической помощи: "
    "8-800-2000-122 (бесплатно, круглосуточно)."
)

_DEFAULT_BLOCK_RESPONSE = (
    "Карты молчат на этот вопрос. Попробуй спросить о чём-то личном."
)


def get_block_response(result: RouterResult) -> str:
    """
    Возвращает текст-заглушку для BLOCKED-запроса.
    Вызывать только когда result.goes_to_classifier == False.
    """
    if result.is_self_harm:
        return _SELF_HARM_RESPONSE
    return _DEFAULT_BLOCK_RESPONSE



# Вспомогательная функция: применить regex-правила
def _apply_rules(text: str) -> RouterResult | None:
    """
    Проходит по BLOCK_PATTERNS.
    Возвращает RouterResult(BLOCKED) при первом совпадении, иначе None.
    """
    for category, patterns in BLOCK_PATTERNS.items():
        if match_any(text, patterns):
            # Исключение: death_general с философским/эмоциональным контекстом
            if category == "death_general" and match_any(text, DEATH_ALLOWLIST):
                continue
            return RouterResult(
                decision=RouterDecision.BLOCKED,
                category=category,
                source="rules",
                score=None,
            )
    return None



# Основная функция
def route(text: str) -> RouterResult:
    """
    Запускает полный пайплайн Safety Router.

    Args:
        text: Вопрос пользователя после базовой очистки (strip, нормализация
              пробелов). Лемматизация не нужна — роутер работает с сырым текстом.
    """

    # ── Уровень 1a: Идиомы — байпас всего (включая s-nlp) ───────────────
    if is_idiom(text):
        return RouterResult(
            decision=RouterDecision.SAFE,
            category=None,
            source="idiom_bypass",
            score=None,
        )

    # ── Уровень 1b: Regex BLOCK_PATTERNS ─────────────────────────────────
    rule_result = _apply_rules(text)
    if rule_result is not None:
        return rule_result

    # ── Уровень 2: inappropriate-модель (только BLOCKED, p >= 0.85) ──────
    inapp = check_inappropriate(text)
    if inapp.is_blocked:
        return RouterResult(
            decision=RouterDecision.BLOCKED,
            category="inappropriate_explicit",
            source="inappropriate_model",
            score=inapp.p_inappropriate,
        )

    # ── Уровень 3a: Словарь бытового раздражения ─────────────────────────
    if is_mild_frustration(text):
        return RouterResult(
            decision=RouterDecision.TOXIC_SAFE,
            category="mild_frustration",
            source="frustration_dict",
            score=None,
        )

    # ── Уровень 3b: Идиомы повторно (перед s-nlp) ────────────────────────
    # s-nlp реагирует на слово «убить» в «убить время» с confidence 0.95.
    # Первая проверка идиом на уровне 1a не поможет, если пользователь
    # написал фразу, которой нет в IDIOMS_ALLOWLIST, но s-nlp всё равно
    # сочтёт токсичной. Повторная проверка здесь — страховка.
    if is_idiom(text):
        return RouterResult(
            decision=RouterDecision.SAFE,
            category=None,
            source="idiom_bypass",
            score=inapp.p_inappropriate,
        )

    # ── Уровень 4: s-nlp toxicity ─────────────────────────────────────────
    toxicity = check_toxicity(text)
    if toxicity.is_toxic:
        return RouterResult(
            decision=RouterDecision.TOXIC_SAFE,
            category="ml_toxic",
            source="toxicity_model",
            score=toxicity.score,
        )

    # ── Всё чисто ─────────────────────────────────────────────────────────
    return RouterResult(
        decision=RouterDecision.SAFE,
        category=None,
        source="passed_all",
        score=inapp.p_inappropriate,
    )