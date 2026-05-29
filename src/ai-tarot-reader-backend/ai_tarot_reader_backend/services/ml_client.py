import httpx

from ai_tarot_reader_backend.configs import get_config


def _ml_base_url() -> str:
    return get_config().ml_layer.base_url


async def validate_message(message: str) -> dict:
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.post(
            f"{_ml_base_url()}/safety-router/validate",
            json={"message": message},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def classify_message(message: str) -> dict:
    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.post(
            f"{_ml_base_url()}/classifier/classify",
            json={"message": message},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()