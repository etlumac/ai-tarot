from fastapi import APIRouter

from ai_tatrot_reader_ml_layer.api.schemas.classifier import (
    ClassificationRequest,
    ClassificationResponse,
)
from ai_tatrot_reader_ml_layer.services.classifier_service import ClassifierService

router = APIRouter(prefix="/classifier", tags=["Classifier"])


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    status_code=200,
)
async def classify_message(body: ClassificationRequest) -> ClassificationResponse:
    return ClassifierService.classify(body)