from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ai_tatrot_reader_ml_layer.entities.enums import ThemeType


# --- POST /classifier/classify ---

class ClassificationRequest(BaseModel):
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ClassificationResponse(BaseModel):
    theme: ThemeType
    confidence: float

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )