import uuid
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
    Tone,
    Theme,
)
from ai_tarot_reader_backend.core.errors import NotFoundError, UnauthorizedError
from ai_tarot_reader_backend.db.data_layer.messages import MessageRepository
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.users import UserRepository
from ai_tarot_reader_backend.entities.enums import (
    MessageRoleType,
    SessionStageType,
    SessionStatusType,
)


class SessionService:

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
    async def get_session(ip: str, session_id: str) -> SessionResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        session = await SessionRepository.get_by_id(
            session_id=UUID(session_id),
            user_id=user.user_id,
            with_messages=True,
        )
        if not session:
            raise NotFoundError(
                user_message="Session not found",
                developer_message=f"Session {session_id} not found for user {ip}",
            )
        return SessionResponse(
            stage=SessionStage(session.stage),
            status=SessionStatus(session.status),
            tone=Tone(session.tone),
            title=session.title,
            theme=Theme(session.theme) if session.theme else None,
            messages=[],
        )

    @staticmethod
    async def create_prediction(ip: str, body: PredictionRequest) -> PredictionResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )

        session_id = uuid.uuid4()

        session = await SessionRepository.create(
            session_id=session_id,
            user_id=user.user_id,
            tone=body.tone,
            stage=SessionStageType.PREDICTION,
            title=None,
        )

        await MessageRepository.create(
            message_id=uuid.uuid4(),
            session_id=session.session_id,
            role=MessageRoleType.USER,
            content=body.message,
        )

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
            raise NotFoundError(
                user_message="Session not found",
                developer_message=f"Session {session_id} not found for user {ip}",
            )

        await SessionRepository.update_state(
            session_id=UUID(session_id),
            status=SessionStatusType.PENDING,
            stage=SessionStageType.CLARIFICATION,
        )

        await MessageRepository.create(
            message_id=uuid.uuid4(),
            session_id=UUID(session_id),
            role=MessageRoleType.USER,
            content=body.message,
        )

        return PredictionResponse(session_id=UUID(session_id))