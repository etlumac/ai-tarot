from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, Request
from ai_tarot_reader_backend.core.database import session_lifespan
from ai_tarot_reader_backend.services.session_service import SessionService
from ai_tarot_reader_backend.services.streaming import StreamingService
from ai_tarot_reader_backend.services.predictions import PredictionService
from ai_tarot_reader_backend.services.ml_client import MLClient
from ai_tarot_reader_backend.services.llm import LLMClient


async def get_current_ip(x_real_ip: Annotated[str, Header()]) -> str:
    return x_real_ip


async def get_session_id(x_session_id: Annotated[str, Header()]) -> str:
    return x_session_id


async def db_session(request: Request) -> AsyncGenerator[None, None]:
    async with session_lifespan(request.app.state.db_connection):
        yield


CurrentIpDep = Annotated[str, Depends(get_current_ip)]
SessionIdDep = Annotated[str, Depends(get_session_id)]
DbSessionDep = Annotated[None, Depends(db_session)]


async def get_ml_client(request: Request) -> MLClient:
    return request.app.state.ml_client


async def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


async def get_predictions_service(request: Request, ml_client: MLClient = Depends(get_ml_client),
                                  llm_client: LLMClient = Depends(get_llm_client)) -> PredictionService:
    return PredictionService(ml_client=ml_client, llm_client=llm_client, db=request.app.state.db_connection)

async def get_sessions_service(predictions_service: PredictionService = Depends(get_predictions_service)) -> SessionService:
    return SessionService(predictions_service)


async def get_streaming_service(request: Request) -> StreamingService:
    return StreamingService(db=request.app.state.db_connection)


SessionServiceDep = Annotated[SessionService, Depends(get_sessions_service)]
StreamingServiceDep = Annotated[StreamingService, Depends(get_streaming_service)]
