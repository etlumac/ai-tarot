import pickle
from typing import List, Optional, Tuple

import numpy as np

from ai_tatrot_reader_ml_layer.entities.enums import ThemeType
from ai_tatrot_reader_ml_layer.ml.classifier.ensemble import (
    LABELS,
    reorder_probas,
    soft_voting,
)

import logging
logger = logging.getLogger(__name__)

_LOGREG_PATH:   Optional[str] = None
_CATBOOST_PATH: Optional[str] = None
_RUBERT_PATH:   Optional[str] = None

_logreg_pipeline  = None
_catboost_model   = None
_rubert_model     = None
_rubert_tokenizer = None
_morph_analyzer   = None
_device           = None


def set_model_paths(logreg: str, catboost: str, rubert: str) -> None:
    global _LOGREG_PATH, _CATBOOST_PATH, _RUBERT_PATH
    _LOGREG_PATH   = logreg
    _CATBOOST_PATH = catboost
    _RUBERT_PATH   = rubert


def load_models() -> None:
    global _logreg_pipeline, _catboost_model
    global _rubert_model, _rubert_tokenizer
    global _morph_analyzer, _device

    import torch
    import pymorphy3
    from catboost import CatBoostClassifier
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Theme classifier device: {_device}")

    # LogReg
    logger.info("Loading TF-IDF + LogReg...")
    with open(_LOGREG_PATH, "rb") as f:
        _logreg_pipeline = pickle.load(f)

    # CatBoost
    logger.info("Loading CatBoost...")
    _catboost_model = CatBoostClassifier()
    _catboost_model.load_model(_CATBOOST_PATH)

    # ruBERT-tiny2
    logger.info("Loading ruBERT-tiny2...")
    _rubert_tokenizer = AutoTokenizer.from_pretrained(_RUBERT_PATH)
    _rubert_model = AutoModelForSequenceClassification.from_pretrained(_RUBERT_PATH)
    _rubert_model.eval()
    _rubert_model.to(_device)

    # Лемматизатор для LogReg и CatBoost
    _morph_analyzer = pymorphy3.MorphAnalyzer()

    logger.info("Theme classifier models loaded")


def _lemmatize(text: str) -> str:
    tokens = text.lower().split()
    lemmas = []
    for token in tokens:
        parsed = _morph_analyzer.parse(token)
        if parsed:
            lemmas.append(parsed[0].normal_form)
    return " ".join(lemmas)


def _predict_logreg(text_lemm: str) -> List[float]:
    raw = _logreg_pipeline.predict_proba([text_lemm])[0].tolist()
    model_labels = list(_logreg_pipeline.classes_)
    return reorder_probas(raw, model_labels)


def _predict_catboost(text_lemm: str) -> List[float]:
    vectorizer = _logreg_pipeline.named_steps["tfidf"]
    tfidf_vec = vectorizer.transform([text_lemm]).toarray()

    extra = np.array([[
        len(text_lemm),
        len(text_lemm.split()),
        int("?" in text_lemm),
        int(any(w in text_lemm.split() for w in ["я", "мой", "моя", "меня", "мне"])),
        int(any(w in text_lemm.split() for w in ["он", "она", "партнёр", "муж", "жена"])),
        int(any(w in text_lemm.split() for w in ["работа", "деньги", "карьера"])),
        int(any(w in text_lemm.split() for w in ["здоровье", "тело", "болеть"])),
    ]])

    features = np.hstack([tfidf_vec, extra])
    raw = _catboost_model.predict_proba(features)[0].tolist()
    model_labels = [str(c) for c in _catboost_model.classes_]
    return reorder_probas(raw, model_labels)


def _predict_rubert(text: str) -> List[float]:
    import torch
    import torch.nn.functional as F

    enc = _rubert_tokenizer(
        text,
        max_length=64,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    enc = {k: v.to(_device) for k, v in enc.items()}

    with torch.no_grad():
        logits = _rubert_model(**enc).logits[0]
        probas = F.softmax(logits, dim=-1).cpu().numpy()

    # Порядок классов ruBERT совпадает с LABELS (задаётся при fine-tuning)
    return probas.tolist()


def predict(text: str) -> Tuple[str, float]:
    if _logreg_pipeline is None or _catboost_model is None or _rubert_model is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Theme classifier models are not loaded. "
                   "Put model files into ai_tatrot_reader_ml_layer/models/ and restart.",
        )

    text_lemm = _lemmatize(text)

    proba_lr = _predict_logreg(text_lemm)
    proba_cb = _predict_catboost(text_lemm)
    proba_rb = _predict_rubert(text)

    return soft_voting(proba_lr, proba_cb, proba_rb)