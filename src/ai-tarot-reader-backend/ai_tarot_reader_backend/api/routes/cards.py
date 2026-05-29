from fastapi import APIRouter, Query

from ai_tarot_reader_backend.api.dependencies import DbSessionDep
from ai_tarot_reader_backend.core.errors import ErrorResponse
from ai_tarot_reader_backend.entities.enums import UIThemeType
from ai_tarot_reader_backend.services.card_service import CardService
from fastapi.responses import Response

router = APIRouter(tags=["Cards"])


@router.get(
    "/cards/{card_id}/image",
    response_class=Response,
    status_code=200,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        404: {"description": "Card not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_card_image(
    card_id: int,
    _: DbSessionDep,
    ui_theme: UIThemeType = Query(default=UIThemeType.PINK, alias="uiTheme"),
) -> Response:
    return await CardService.get_card_image(card_id=card_id, ui_theme=ui_theme)