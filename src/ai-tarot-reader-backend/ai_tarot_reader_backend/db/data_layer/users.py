from typing import Optional
from uuid import UUID

from sqlalchemy import select, update

from ai_tarot_reader_backend.core.transactions import transactional
from ai_tarot_reader_backend.db.orm import UserModel
from ai_tarot_reader_backend.entities.domain import UserEntity


class UserRepository:
    @staticmethod
    async def get_by_ip(ip_address: str) -> Optional[UserEntity]:
        async with transactional() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.ip_address == ip_address)
            )
            user = result.scalar_one_or_none()
            return UserEntity.model_validate(user) if user else None

    @staticmethod
    async def create(
        user_id: UUID,
        ip_address: str,
        name: str,
        description: Optional[str] = None
    ) -> UserEntity:
        async with transactional() as session:
            new_user = UserModel(
                user_id=user_id,
                ip_address=ip_address,
                name=name,
                description=description
            )
            session.add(new_user)
            return UserEntity.model_validate(new_user)

    @staticmethod
    async def update(
        user_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[UserEntity]:
        async with transactional() as session:
            stmt = update(UserModel).where(UserModel.user_id == user_id)
            if name is not None:
                stmt = stmt.values(name=name)
            if description is not None:
                stmt = stmt.values(description=description)

            stmt = stmt.returning(UserModel)
            result = await session.execute(stmt)
            updated = result.scalar_one_or_none()
            return UserEntity.model_validate(updated) if updated else None