from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from ai_tarot_reader_backend.core.transactions import transactional
from ai_tarot_reader_backend.db.orm import SessionModel
from ai_tarot_reader_backend.entities.domain import SessionEntity
from ai_tarot_reader_backend.entities.enums import (
    ToneType, SessionStageType, SessionStatusType, ThemeType
)


class SessionRepository:
    @staticmethod
    async def create(
            session_id: UUID,
            user_id: UUID,
            tone: ToneType,
            stage: SessionStageType,
            title: Optional[str] = None
    ) -> SessionEntity:
        async with transactional() as session:
            new_session = SessionModel(
                session_id=session_id,
                user_id=user_id,
                tone=tone,
                stage=stage,
                status=SessionStatusType.PENDING,
                title=title,
                prediction_cards=[],
                clarification_card=None
            )
            session.add(new_session)
            return SessionEntity.model_validate(new_session)

    @staticmethod
    async def get_by_id(
            session_id: UUID,
            user_id: Optional[UUID] = None,
    ) -> Optional[SessionEntity]:
        async with transactional() as session:
            stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            if user_id:
                stmt = stmt.where(SessionModel.user_id == user_id)

            result = await session.execute(stmt)
            session_obj = result.unique().scalar_one_or_none()
            return SessionEntity.model_validate(session_obj) if session_obj else None

    @staticmethod
    async def get_by_user(user_id: UUID) -> List[SessionEntity]:
        async with transactional() as session:
            stmt = (
                select(SessionModel)
                .where(SessionModel.user_id == user_id)
                .order_by(SessionModel.created_at.desc())
            )
            result = await session.execute(stmt)
            return [SessionEntity.model_validate(obj) for obj in result.scalars().all()]

    @staticmethod
    async def update_state(
            session_id: UUID,
            status: Optional[SessionStatusType] = None,
            stage: Optional[SessionStageType] = None,
            prediction_cards: Optional[List[int]] = None,
            clarification_card: Optional[int] = None,
            theme: Optional[ThemeType] = None,
            title: Optional[str] = None
    ) -> None:
        update_data = {
            "status": status,
            "stage": stage,
            "prediction_cards": prediction_cards,
            "clarification_card": clarification_card,
            "theme": theme,
            "title": title,
        }
        filtered_data = {k: v for k, v in update_data.items() if v is not None}

        if not filtered_data:
            return

        async with transactional() as session:
            stmt = (
                update(SessionModel)
                .where(SessionModel.session_id == session_id)
                .values(filtered_data)
            )
            await session.execute(stmt)