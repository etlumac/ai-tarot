from enum import Enum
from typing import List, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ai_tarot_reader_backend.api.schemas.sessions import (
    Arcana,
    CardSchema,
    MessageSchema,
    MessageSchemaType,
    Role,
    Theme,
)


# --- GET /session/streaming ---

class SseEvent(str, Enum):
    error = "error"
    theme = "theme"
    cards = "cards"
    message = "message"
    session_title = "sessionTitle"


class ThemeSchemaType(BaseModel):
    theme: Theme

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CardsSchemaType(BaseModel):
    messages: List[CardSchema]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class MessagesSchemaType(BaseModel):
    messages: List[MessageSchemaType]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class SessionTitleSchemaType(BaseModel):
    title: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ErrorSchemaType(BaseModel):
    error_type: str
    error_status_code: int
    user_message: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


SseData = Union[
    ErrorSchemaType,
    ThemeSchemaType,
    CardsSchemaType,
    MessagesSchemaType,
    SessionTitleSchemaType,
]


class SseEnvelope(BaseModel):
    event: SseEvent
    data: SseData
    id: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )