from typing import List
from uuid import UUID

from sqlalchemy import select

from ai_tarot_reader_backend.core.transactions import transactional
from ai_tarot_reader_backend.db.orm import MessageModel
from ai_tarot_reader_backend.entities.domain import MessageEntity
from ai_tarot_reader_backend.entities.enums import MessageRoleType


class MessageRepository:
    @staticmethod
    async def create(
        message_id: UUID,
        session_id: UUID,
        role: MessageRoleType,
        content: str
    ) -> MessageEntity:
        async with transactional() as session:
            new_msg = MessageModel(
                message_id=message_id,
                session_id=session_id,
                role=role,
                content=content
            )
            session.add(new_msg)
            return MessageEntity.model_validate(new_msg)

    @staticmethod
    async def get_by_session(session_id: UUID) -> List[MessageEntity]:
        async with transactional() as session:
            stmt = (
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.created_at)
            )
            result = await session.execute(stmt)
            return [MessageEntity.model_validate(msg) for msg in result.scalars().all()]