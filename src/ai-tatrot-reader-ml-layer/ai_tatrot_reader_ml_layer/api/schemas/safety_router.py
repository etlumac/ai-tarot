from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ai_tatrot_reader_ml_layer.ml.safety_router.router import RouterDecision


# --- POST /safety-router/validate ---

class ValidationRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ValidationResponse(BaseModel):
    decision: RouterDecision
    category: str | None
    source: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )