from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from ai_tatrot_reader_ml_layer.api.routes.classifier import router as classifier_router
from ai_tatrot_reader_ml_layer.api.routes.safety_router import router as safety_router
from ai_tatrot_reader_ml_layer.ml.classifier import theme_classifier
from ai_tatrot_reader_ml_layer.ml.safety_router.models import (
    _get_inappropriate_pipe,
    _get_toxicity_pipe,
)

import logging
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent

LOGREG_PATH   = APP_DIR / "models" / "tfidf_logreg_v1.pkl"
CATBOOST_PATH = APP_DIR / "models" / "catboost_v1.cbm"
RUBERT_PATH   = APP_DIR / "models" / "rubert_tiny2_tarot"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _get_inappropriate_pipe()
    _get_toxicity_pipe()

    if LOGREG_PATH.exists() and CATBOOST_PATH.exists() and RUBERT_PATH.exists():
        theme_classifier.set_model_paths(
            logreg=str(LOGREG_PATH),
            catboost=str(CATBOOST_PATH),
            rubert=str(RUBERT_PATH),
        )
        theme_classifier.load_models()
    else:
        logger.warning(
            "Theme classifier models not found in %s — "
            "POST /classifier/classify will return 503 until models are loaded. "
            "Put tfidf_logreg_v1.pkl, catboost_v1.cbm, rubert_tiny2_tarot/ "
            "into ai_tatrot_reader_ml_layer/models/",
            APP_DIR / "models",
        )

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Tarot ML Layer",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(safety_router)
    app.include_router(classifier_router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)