import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from config import config
from database.database import init_db
from bot.handlers import start, voice, profiles, profile_create, profile_edit, history, profile_export
from bot.middlewares.user_middleware import UserMiddleware
from utils.logger import logger


async def set_bot_commands(bot: Bot):
    """Set bot commands for the menu"""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="profiles", description="Выбрать профиль"),
        BotCommand(command="edit", description="Редактировать профиль"),
        BotCommand(command="history", description="История обработок"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands)

async def main():
    """Main entry point for the bot"""

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ {e}")
        print("\nПожалуйста, проверьте файл .env и добавьте недостающие API ключи.\n")
        return

    # Initialize database
    logger.info("Initializing database...")
    print("🔧 Инициализация базы данных...")
    init_db()
    print("✅ База данных готова\n")

    # Initialize bot and dispatcher
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(voice.router)
    dp.include_router(profiles.router)
    dp.include_router(profile_create.router)
    dp.include_router(profile_edit.router)
    dp.include_router(history.router)
    dp.include_router(profile_export.router)

    # Set bot commands menu
    await set_bot_commands(bot)

    # Start polling
    logger.info("Bot started")
    print("🚀 Бот запущен и готов к работе!")
    print(f"📱 Модель LLM: {config.OPENROUTER_MODEL}")
    print(f"🎤 Транскрипция: Groq Whisper API")
    print("\n⚠️  Для работы с голосовыми сообщениями нужен Groq API ключ!")
    print("   Получите бесплатный ключ на: https://console.groq.com/keys")
    print("   И добавьте его в файл .env\n")
    print("Нажмите Ctrl+C для остановки бота\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")
        logger.info("Bot stopped by user")
