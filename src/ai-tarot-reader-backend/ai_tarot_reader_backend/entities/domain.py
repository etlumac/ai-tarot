import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from ai_tarot_reader_backend.entities.enums import (
    ToneType, SessionStageType, SessionStatusType, ThemeType,
    MessageRoleType, UIThemeType, ArcanaType
)


class UserEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[uuid.UUID] = uuid.uuid7()
    ip_address: str
    name: str
    description: Optional[str] = None


class TarotCardEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    card_id: int
    title: str
    meaning: str
    arcana: ArcanaType
    is_reversed: bool = False


class CardImageEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    image_id: int
    card_id: int
    ui_theme: UIThemeType
    image: bytes


class MessageEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: Optional[uuid.UUID] = uuid.uuid7()
    session_id: uuid.UUID
    role: MessageRoleType
    content: str
    created_at: Optional[datetime] = None


class SessionEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: Optional[uuid.UUID] = uuid.uuid7()
    user_id: uuid.UUID
    tone: ToneType
    status: SessionStatusType
    stage: SessionStageType
    theme: Optional[ThemeType] = None
    title: Optional[str] = None

    prediction_cards: Optional[List[int]] = Field(default_factory=list)
    clarification_card: Optional[int] = None
