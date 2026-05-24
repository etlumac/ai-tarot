from ai_tatrot_reader_ml_layer.api.schemas.safety_router import (
    ValidationRequest,
    ValidationResponse,
)
from ai_tatrot_reader_ml_layer.ml.safety_router.router import route


class SafetyRouterService:

    @staticmethod
    def validate(body: ValidationRequest) -> ValidationResponse:
        result = route(body.message)
        return ValidationResponse(
            decision=result.decision,
            category=result.category,
            source=result.source,
        )