from openai import AsyncOpenAI
from config import config

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config.OPENROUTER_API_KEY
)

async def format_text(transcribed_text: str, system_prompt: str) -> str:
    """Format transcribed text using OpenRouter LLM"""

    try:
        response = await client.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcribed_text}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"LLM formatting error: {str(e)}")
