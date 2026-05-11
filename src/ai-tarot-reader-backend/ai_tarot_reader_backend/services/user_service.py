from ai_tarot_reader_backend.api.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
)


class UserService:

    @staticmethod
    async def create_user(ip: str, body: UserCreateRequest) -> None:
        pass

    @staticmethod
    async def update_user(ip: str, body: UserUpdateRequest) -> UserUpdateResponse:
        pass

    @staticmethod
    async def get_user(ip: str) -> UserResponse:
        pass