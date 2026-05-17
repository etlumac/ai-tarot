from typing import ClassVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseAppError(Exception):
    error_code: ClassVar[str] = "Exception"
    status_code: ClassVar[int] = 500

    def __init__(
        self,
        user_message: str,
        developer_message: str,
    ) -> None:
        self.user_message = user_message
        self.developer_message = developer_message


class ErrorResponse(BaseModel):
    service_name: str
    error_code: str
    user_message: str
    developer_message: str
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class InfrastructureError(BaseAppError):
    error_code = "InfrastructureError"
    status_code = 503


class ValidationError(BaseAppError):
    error_code: ClassVar[str] = "ValidationError"
    status_code: ClassVar[int] = 400


class UnauthorizedError(BaseAppError):
    error_code: ClassVar[str] = "Unauthorized"
    status_code: ClassVar[int] = 401


class NotFoundError(BaseAppError):
    error_code: ClassVar[str] = "NotFoundError"
    status_code: ClassVar[int] = 404


class ResourceAlreadyExistsError(BaseAppError):
    error_code: ClassVar[str] = "ResourceAlreadyExistsError"
    status_code: ClassVar[int] = 409


class IncompatibleParamsError(BaseAppError):
    error_code: ClassVar[str] = "IncompatibleParamsError"
    status_code: ClassVar[int] = 422
