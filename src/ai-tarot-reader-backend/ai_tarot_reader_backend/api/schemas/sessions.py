from enum import Enum
from typing import List, Literal, Optional, Union, Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# --- общие схемы ---

class SessionStage(str, Enum):
    prediction = "prediction"
    clarification = "clarification"


class SessionStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    failed = "failed"


class Tone(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class Theme(str, Enum):
    career = "career"
    love = "love"
    self = "self"
    social = "social"
    health = "health"
    other = "other"


class Arcana(str, Enum):
    major = "major"
    minor = "minor"


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


# --- GET /sessions ---

class SessionListItem(BaseModel):
    session_id: UUID
    title: Optional[str]
    stage: SessionStage
    status: SessionStatus

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# --- POST /session/prediction ---

class PredictionRequest(BaseModel):
    tone: Tone
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class PredictionResponse(BaseModel):
    session_id: UUID

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# --- GET /session ---

class MessageSchema(BaseModel):
    object_type: Literal["message"]
    role: Role
    content: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class CardSchema(BaseModel):
    object_type: Literal["card"]
    card_id: UUID
    title: str
    meaning: str
    arcana: Arcana
    reversed: bool

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


MessageSchemaType = Annotated[
    Union[MessageSchema, CardSchema],
    Field(discriminator="object_type"),
]


class SessionResponse(BaseModel):
    stage: SessionStage
    status: SessionStatus
    tone: Tone
    title: Optional[str]
    theme: Optional[Theme]
    messages: List[MessageSchemaType]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# --- POST /session/clarification ---

class ClarificationRequest(BaseModel):
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )