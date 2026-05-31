import uuid
import asyncio
from uuid import UUID

from ai_tarot_reader_backend.api.schemas.sessions import (
    ClarificationRequest,
    PredictionRequest,
    PredictionResponse,
    SessionListItem,
    SessionListResponse,
    SessionResponse,
    SessionStage,
    SessionStatus,
    MessageSchema,
    CardSchema,
    MessageSchemaType,
    Tone,
    Theme,
)
from ai_tarot_reader_backend.core.errors import ForbiddenError, UnauthorizedError
from ai_tarot_reader_backend.db.data_layer.messages import MessageRepository
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.users import UserRepository
from ai_tarot_reader_backend.db.data_layer.cards import CardGraphRepository
from ai_tarot_reader_backend.entities.domain import SessionEntity
from ai_tarot_reader_backend.entities.enums import (
    MessageRoleType,
    SessionStageType,
    SessionStatusType,
    ObjectType
)
from ai_tarot_reader_backend.services.predictions import PredictionService


class SessionService:

    def __init__(self, prediction_service: PredictionService):
        self.prediction_service = prediction_service

    @staticmethod
    async def get_sessions_by_ip(ip: str) -> SessionListResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        sessions = await SessionRepository.get_by_user(user.user_id)
        return SessionListResponse(
            sessions=[
                SessionListItem(
                    session_id=s.session_id,
                    title=s.title,
                    stage=SessionStage(s.stage),
                    status=SessionStatus(s.status),
                )
                for s in sessions
            ]
        )

    @staticmethod
    async def __form_card_messages(session: SessionEntity) -> list[CardSchema]:
        prediction_cards_ids = session.prediction_cards
        cards =[]
        if prediction_cards_ids:
            for card_id in prediction_cards_ids:
                card_info = await CardGraphRepository.get_card_data(card_id)

                title = card_info["title"].strip('"')
                meaning = card_info["meaning"].strip('"')
                arcana = card_info["arcana"].strip('"')
                reversed = card_info["reversed"]
                card = CardSchema.model_validate({
                    "objectType": ObjectType.CARD.value,
                    "cardId": card_id,
                    "title": title,
                    "arcana": arcana,
                    "meaning": meaning,
                    "reversed": reversed
                })
                cards.append(card)
        if session.clarification_card:
            clarification_card_info = await CardGraphRepository.get_card_data(session.clarification_card)

            title = clarification_card_info["title"].strip('"')
            meaning = clarification_card_info["meaning"].strip('"')
            arcana = clarification_card_info["arcana"].strip('"')
            reversed = clarification_card_info["reversed"]
            card = CardSchema.model_validate({
                "objectType": ObjectType.CARD.value,
                "cardId": session.clarification_card,
                "title": title,
                "arcana": arcana,
                "meaning": meaning,
                "reversed": reversed
            })
            cards.append(card)
        return cards

    async def get_session(self, ip: str, session_id: str) -> SessionResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        session = await SessionRepository.get_by_id(
            session_id=UUID(session_id),
            user_id=user.user_id,
        )
        if not session:
            raise ForbiddenError(
                user_message="Session not found",
                developer_message=f"Session {session_id} not found for user {ip}",
            )
        messages = await MessageRepository.get_by_session(session.session_id)
        text_messages = [MessageSchema(object_type="message", role=message.role, content=message.content) for message in messages]
        card_messages = await self.__form_card_messages(session)
        text_messages.extend(card_messages)
        return SessionResponse(
            stage=SessionStage(session.stage),
            status=SessionStatus(session.status),
            tone=Tone(session.tone),
            title=session.title,
            theme=Theme(session.theme) if session.theme else None,
            messages=text_messages,
        )

    async def create_prediction(self, ip: str, body: PredictionRequest) -> PredictionResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )

        session_id = uuid.uuid7()

        session = await SessionRepository.create(
            session_id=session_id,
            user_id=user.user_id,
            tone=body.tone,
            stage=SessionStageType.PREDICTION,
            title=None,
        )

        await MessageRepository.create(
            message_id=uuid.uuid7(),
            session_id=session.session_id,
            role=MessageRoleType.USER,
            content=body.message,
        )
        asyncio.create_task(self.prediction_service.prediction_pipeline(session_id, body.message, body.tone))

        return PredictionResponse(session_id=session.session_id)

    @staticmethod
    async def create_clarification(
        ip: str,
        session_id: str,
        body: ClarificationRequest,
    ) -> PredictionResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )

        session = await SessionRepository.get_by_id(
            session_id=UUID(session_id),
            user_id=user.user_id,
        )
        if not session:
            raise ForbiddenError(
                user_message="Session not found",
                developer_message=f"Session {session_id} not found for user {ip}",
            )

        await SessionRepository.update_state(
            session_id=UUID(session_id),
            status=SessionStatusType.PENDING,
            stage=SessionStageType.CLARIFICATION,
        )

        await MessageRepository.create(
            message_id=uuid.uuid7(),
            session_id=UUID(session_id),
            role=MessageRoleType.USER,
            content=body.message,
        )

        return PredictionResponse(session_id=UUID(session_id))