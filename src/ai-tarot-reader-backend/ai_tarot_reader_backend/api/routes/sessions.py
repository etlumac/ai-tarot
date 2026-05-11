from fastapi import APIRouter

from ai_tarot_reader_backend.api.dependencies import CurrentIpDep, SessionIdDep
from ai_tarot_reader_backend.api.schemas.sessions import (
    PredictionRequest,
    PredictionResponse,
    SessionListResponse,
    SessionResponse,
    ClarificationRequest,
)
from ai_tarot_reader_backend.core.errors import ErrorResponse
from ai_tarot_reader_backend.services.session_service import SessionService

router = APIRouter(tags=["Sessions"])


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=200,
    responses={
        401: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_sessions(ip: CurrentIpDep) -> SessionListResponse:
    return await SessionService.get_sessions_by_ip(ip)



@router.post(
    "/session/prediction",
    response_model=PredictionResponse,
    status_code=202,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        401: {"description": "User not found", "model": ErrorResponse},
        422: {"description": "Wrong combination of input parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_prediction(
    body: PredictionRequest,
    ip: CurrentIpDep,
) -> PredictionResponse:
    return await SessionService.create_prediction(ip=ip, body=body)


@router.get(
    "/session",
    response_model=SessionResponse,
    status_code=200,
    responses={
        401: {"description": "User not found", "model": ErrorResponse},
        403: {"description": "Session not found or does not belong to user", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_session(
    ip: CurrentIpDep,
    session_id: SessionIdDep,
) -> SessionResponse:
    return await SessionService.get_session(ip=ip, session_id=session_id)


@router.post(
    "/session/clarification",
    response_model=PredictionResponse,
    status_code=202,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        401: {"description": "User not found", "model": ErrorResponse},
        422: {"description": "Wrong combination of input parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_clarification(
        body: ClarificationRequest,
        ip: CurrentIpDep,
        session_id: SessionIdDep,
) -> PredictionResponse:
    return await SessionService.create_clarification(ip=ip, session_id=session_id, body=body)


