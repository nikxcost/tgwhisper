import aiohttp
from io import BytesIO
from config import config

async def transcribe_voice(audio_file: BytesIO) -> str:
    """Transcribe voice using Groq Whisper API"""

    if not config.GROQ_API_KEY:
        raise Exception("GROQ_API_KEY not configured. Get your free API key at https://console.groq.com/keys")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}"
    }

    # Prepare form data
    data = aiohttp.FormData()
    data.add_field('file', audio_file, filename='voice.ogg', content_type='audio/ogg')
    data.add_field('model', 'whisper-large-v3')
    data.add_field('language', 'ru')  # Russian language

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Groq API error: {response.status} - {error_text}")

            result = await response.json()
            return result.get('text', '')
