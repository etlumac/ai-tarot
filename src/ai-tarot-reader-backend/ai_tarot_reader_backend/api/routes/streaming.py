from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ai_tarot_reader_backend.api.dependencies import CurrentIpDep, DbSessionDep, SessionIdDep, StreamingServiceDep
from ai_tarot_reader_backend.core.errors import ErrorResponse

router = APIRouter(tags=["Streaming"])


@router.get(
    "/session/streaming",
    response_class=StreamingResponse,
    status_code=200,
    responses={
        401: {"description": "User not found", "model": ErrorResponse},
        403: {"description": "Session not found or does not belong to user", "model": ErrorResponse},
        409: {"description": "Session staus is not compatible", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_session_streaming(
    request: Request,
    ip: CurrentIpDep,
    session_id: SessionIdDep,
    streaming_service: StreamingServiceDep,
    _: DbSessionDep,
) -> StreamingResponse:
    await streaming_service.validate_request(session_id=UUID(session_id), ip=ip)
    return StreamingResponse(
        streaming_service.event_generator(session_id=UUID(session_id), request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # отключает буферизацию в nginx
        },
    )