from uuid import UUID

from fastapi.responses import FileResponse


class CardService:

    @staticmethod
    async def get_card_image(card_id: UUID) -> FileResponse:
        pass