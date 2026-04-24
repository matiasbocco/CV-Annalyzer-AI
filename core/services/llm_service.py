from openai import AsyncOpenAI
from core.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def test_connection() -> str:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
    )
    return response.choices[0].message.content
