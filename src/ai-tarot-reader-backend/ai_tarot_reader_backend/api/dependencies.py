from typing import Annotated
from fastapi import Depends, Header


async def get_current_ip(x_real_ip: Annotated[str, Header()]) -> str:
    return x_real_ip


async def get_session_id(x_session_id: Annotated[str, Header()]) -> str:
    return x_session_id


CurrentIpDep = Annotated[str, Depends(get_current_ip)]
SessionIdDep = Annotated[str, Depends(get_session_id)]