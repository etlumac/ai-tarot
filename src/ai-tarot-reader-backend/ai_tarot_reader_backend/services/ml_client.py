import httpx

from ai_tarot_reader_backend.configs import get_config

class MLClient:

    def __init__(self):
        self.client = httpx.AsyncClient(trust_env=False, base_url=get_config().ml_layer.base_url)

    async def validate_message(self, message: str) -> dict:
        response = await self.client.post(
            "/safety-router/validate",
            json={"message": message},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


    async def classify_message(self, message: str) -> dict:
        response = await self.client.post(
            "/classifier/classify",
            json={"message": message},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()