from typing import AsyncGenerator

from ai_tarot_reader_backend.api.schemas.streaming import SseEnvelope


class StreamingService:

    @staticmethod
    async def stream(ip: str, session_id: str) -> AsyncGenerator[str, None]:
        yield ""