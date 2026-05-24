from fastapi import APIRouter

from ai_tatrot_reader_ml_layer.api.schemas.safety_router import (
    ValidationRequest,
    ValidationResponse,
)
from ai_tatrot_reader_ml_layer.services.safety_router_service import SafetyRouterService

router = APIRouter(prefix="/safety-router", tags=["Safety Router"])


@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=200,
)
async def validate_message(body: ValidationRequest) -> ValidationResponse:
    return SafetyRouterService.validate(body)