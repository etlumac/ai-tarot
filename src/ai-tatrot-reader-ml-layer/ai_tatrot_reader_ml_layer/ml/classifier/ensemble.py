from typing import Dict, List, Optional, Tuple

import numpy as np

from ai_tatrot_reader_ml_layer.entities.enums import ThemeType

LABELS: List[str] = [
    ThemeType.LOVE,
    ThemeType.SELF,
    ThemeType.SOCIAL,
    ThemeType.HEALTH,
    ThemeType.CAREER,
]

WEIGHTS = {
    "logreg":   0.20,
    "catboost": 0.20,
    "rubert":   0.60,
}

THRESHOLD = 0.30


def soft_voting(
    proba_logreg: List[float],
    proba_catboost: List[float],
    proba_rubert: List[float],
) -> Tuple[str, float]:

    avg = (
        WEIGHTS["logreg"]   * np.array(proba_logreg) +
        WEIGHTS["catboost"] * np.array(proba_catboost) +
        WEIGHTS["rubert"]   * np.array(proba_rubert)
    )

    best_idx = int(np.argmax(avg))
    confidence = float(avg[best_idx])

    if confidence < THRESHOLD:
        return ThemeType.OTHER, confidence

    return LABELS[best_idx], confidence


def reorder_probas(raw_probas: List[float], model_labels: List[str]) -> List[float]:
    label_to_prob = dict(zip(model_labels, raw_probas))
    return [label_to_prob.get(label, 0.0) for label in LABELS]