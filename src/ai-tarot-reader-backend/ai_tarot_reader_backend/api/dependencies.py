from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, Request
from ai_tarot_reader_backend.core.database import session_lifespan


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