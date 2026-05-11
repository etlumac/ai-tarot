from ai_tarot_reader_backend.api.schemas.sessions import (
    PredictionRequest,
    PredictionResponse,
    SessionListResponse,
    SessionResponse,
    ClarificationRequest,
)


class SessionService:

    @staticmethod
    async def get_sessions_by_ip(ip: str) -> SessionListResponse:
        pass

    @staticmethod
    async def create_prediction(ip: str, body: PredictionRequest) -> PredictionResponse:
        pass

    @staticmethod
    async def get_session(ip: str, session_id: str) -> SessionResponse:
        pass

    @staticmethod
    async def create_clarification(
            ip: str,
            session_id: str,
            body: ClarificationRequest,
    ) -> PredictionResponse:
        pass