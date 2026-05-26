from typing import Optional

from sqlalchemy import select

from ai_tarot_reader_backend.core.transactions import transactional
from ai_tarot_reader_backend.db.orm import ImageModel
from ai_tarot_reader_backend.entities.domain import CardImageEntity
from ai_tarot_reader_backend.entities.enums import UIThemeType


class CardImageRepository:
    @staticmethod
    async def get_by_card_id(card_id: int, ui_theme: UIThemeType) -> Optional[CardImageEntity]:
        async with transactional() as session:
            stmt = select(ImageModel).where(
                ImageModel.card_id == card_id,
                ImageModel.ui_theme == ui_theme
            )
            result = await session.execute(stmt)
            image = result.scalar_one_or_none()
            return CardImageEntity.model_validate(image) if image else None