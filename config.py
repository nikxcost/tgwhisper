import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")

    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = "xiaomi/mimo-v2-flash:free"

    # Groq Whisper
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")

    # Limits
    MAX_VOICE_DURATION: int = 300  # 5 minutes
    MAX_CUSTOM_PROFILES: int = 10  # Per user

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "bot.log"

    def validate(self):
        """Validate that all required config is present"""
        required = [
            ("TELEGRAM_BOT_TOKEN", self.TELEGRAM_BOT_TOKEN),
            ("OPENROUTER_API_KEY", self.OPENROUTER_API_KEY),
        ]

        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        if not self.GROQ_API_KEY:
            print("⚠️  WARNING: GROQ_API_KEY not set. Voice transcription will not work!")
            print("   Get your free API key at: https://console.groq.com/keys")

config = Config()
