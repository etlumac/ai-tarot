from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# --- POST /user ---

class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# --- PATCH /user ---

class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class UserUpdateResponse(BaseModel):
    name: Optional[str]
    description: Optional[str]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# --- GET /user ---

class UserResponse(BaseModel):
    name: str
    description: Optional[str]

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )