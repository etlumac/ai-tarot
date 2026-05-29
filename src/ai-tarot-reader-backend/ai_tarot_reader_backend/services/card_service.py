from fastapi.responses import Response

from ai_tarot_reader_backend.core.errors import NotFoundError
from ai_tarot_reader_backend.db.data_layer.images import CardImageRepository
from ai_tarot_reader_backend.entities.enums import UIThemeType


class CardService:

    @staticmethod
    async def get_card_image(card_id: int, ui_theme: UIThemeType) -> Response:
        image = await CardImageRepository.get_by_card_id(card_id, ui_theme)
        if not image:
            raise NotFoundError(
                user_message="Card not found",
                developer_message=f"Card {card_id} with theme {ui_theme.value} not found",
            )
        return Response(
            content=image.image,
            media_type="image/webp",
        )