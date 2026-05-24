from ai_tatrot_reader_ml_layer.api.schemas.classifier import (
    ClassificationRequest,
    ClassificationResponse,
)
from ai_tatrot_reader_ml_layer.ml.classifier import theme_classifier


class ClassifierService:

    @staticmethod
    def classify(body: ClassificationRequest) -> ClassificationResponse:
        theme, confidence = theme_classifier.predict(body.message)
        return ClassificationResponse(theme=theme, confidence=confidence)