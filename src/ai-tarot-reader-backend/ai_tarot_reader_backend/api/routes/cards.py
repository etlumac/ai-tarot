from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ai_tarot_reader_backend.core.errors import ErrorResponse
from ai_tarot_reader_backend.services.card_service import CardService

router = APIRouter(tags=["Cards"])


@router.get(
    "/cards/{card_id}/image",
    response_class=FileResponse,
    status_code=200,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        404: {"description": "Card not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_card_image(card_id: UUID) -> FileResponse:
    return await CardService.get_card_image(card_id)