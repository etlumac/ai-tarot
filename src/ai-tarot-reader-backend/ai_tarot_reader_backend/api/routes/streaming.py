from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ai_tarot_reader_backend.api.dependencies import CurrentIpDep, DbSessionDep, SessionIdDep
from ai_tarot_reader_backend.core.errors import ErrorResponse
from ai_tarot_reader_backend.services.streaming_service import StreamingService

router = APIRouter(tags=["Streaming"])


@router.get(
    "/session/streaming",
    response_class=StreamingResponse,
    status_code=200,
    responses={
        401: {"description": "User not found", "model": ErrorResponse},
        403: {"description": "Session not found or does not belong to user", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_session_streaming(
    ip: CurrentIpDep,
    session_id: SessionIdDep,
    _: DbSessionDep,
) -> StreamingResponse:
    return StreamingResponse(
        StreamingService.stream(ip=ip, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # отключает буферизацию в nginx
        },
    )