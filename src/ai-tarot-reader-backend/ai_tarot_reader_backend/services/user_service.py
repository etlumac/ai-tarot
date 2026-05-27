import uuid
from ai_tarot_reader_backend.api.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)
from ai_tarot_reader_backend.core.errors import NotFoundError, ResourceAlreadyExistsError
from ai_tarot_reader_backend.db.data_layer.users import UserRepository


class UserService:

    @staticmethod
    async def create_user(ip: str, body: UserCreateRequest) -> None:
        existing = await UserRepository.get_by_ip(ip)
        if existing:
            raise ResourceAlreadyExistsError(
                user_message="User already exists",
                developer_message=f"User with ip={ip} already exists",
            )
        await UserRepository.create(
            user_id=uuid.uuid7(),
            ip_address=ip,
            name=body.name,
            description=body.description,
        )

    @staticmethod
    async def update_user(ip: str, body: UserUpdateRequest) -> UserUpdateResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise NotFoundError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        updated = await UserRepository.update(
            user_id=user.user_id,
            name=body.name,
            description=body.description,
        )
        return UserUpdateResponse(
            name=updated.name,
            description=updated.description,
        )

    @staticmethod
    async def get_user(ip: str) -> UserResponse:
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise NotFoundError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        return UserResponse(name=user.name, description=user.description)