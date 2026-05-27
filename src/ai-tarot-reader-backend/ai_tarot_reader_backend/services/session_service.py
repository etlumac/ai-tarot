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
)

from ai_tarot_reader_backend.core.errors import NotFoundError, UnauthorizedError
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.users import UserRepository


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
                    stage=SessionStage(s.stage.value),
                    status=SessionStatus(s.status.value),
                )
                for s in sessions
            ]
        )

    @staticmethod
    async def create_prediction(ip: str, body: PredictionRequest) -> PredictionResponse:
        pass

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
            stage=SessionStage(session.stage.value),
            status=SessionStatus(session.status.value),
            tone=session.tone,
            title=session.title,
            theme=session.theme,
            messages=[],
        )

    @staticmethod
    async def create_clarification(
            ip: str,
            session_id: str,
            body: ClarificationRequest,
    ) -> PredictionResponse:
        pass