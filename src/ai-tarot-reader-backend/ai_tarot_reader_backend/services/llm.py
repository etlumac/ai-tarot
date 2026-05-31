from openai import AsyncOpenAI
from ai_tarot_reader_backend.configs import get_config


class LLMClient:

    def __init__(self):
        config = get_config()
        self.client = AsyncOpenAI(
            base_url=config.open_router.base_url,
            api_key=config.open_router.api_key.get_secret_value(),
        )
        self.model = config.open_router.model

    async def __call__(self, messages: list[dict[str, str]], max_tokens: int = 1000) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def close(self):
        await self.client.close()