from fastapi import APIRouter, Response

from ai_tarot_reader_backend.api.dependencies import CurrentIpDep
from ai_tarot_reader_backend.api.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from ai_tarot_reader_backend.core.errors import ErrorResponse
from ai_tarot_reader_backend.services.user_service import UserService

router = APIRouter(tags=["User"])


@router.post(
    "/user",
    status_code=200,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_user(
    body: UserCreateRequest,
    ip: CurrentIpDep,
) -> Response:
    await UserService.create_user(ip=ip, body=body)
    return Response(status_code=200)


@router.patch(
    "/user",
    response_model=UserUpdateResponse,
    status_code=200,
    responses={
        400: {"description": "Validation error", "model": ErrorResponse},
        401: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def update_user(
    body: UserUpdateRequest,
    ip: CurrentIpDep,
) -> UserUpdateResponse:
    return await UserService.update_user(ip=ip, body=body)


@router.get(
    "/user",
    response_model=UserResponse,
    status_code=200,
    responses={
        401: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_user(ip: CurrentIpDep) -> UserResponse:
    return await UserService.get_user(ip=ip)