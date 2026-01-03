from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base, Profile
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")

engine = create_engine(DATABASE_URL, echo=False)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def migrate_db():
    """Run database migrations"""
    inspector = inspect(engine)

    # Check if profiles table exists
    if 'profiles' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('profiles')]

        # Add parent_id column if it doesn't exist
        if 'parent_id' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE profiles ADD COLUMN parent_id INTEGER REFERENCES profiles(id)"))
                conn.commit()
            print("✅ Migration: Added parent_id column to profiles table")


def init_db():
    """Initialize database and create default profiles"""
    Base.metadata.create_all(engine)

    # Run migrations for existing databases
    migrate_db()

    # Create default profiles if they don't exist
    session = Session()
    try:
        if session.query(Profile).filter_by(is_default=True).count() == 0:
            default_profiles = [
                Profile(
                    name="Деловая переписка",
                    description="Форматирование для деловых писем и официальных сообщений",
                    system_prompt="""Ты - ассистент для форматирования голосовых сообщений в деловой текст.

Твоя задача:
- Преобразовать разговорную речь в формальный деловой стиль
- Структурировать текст с четкими абзацами
- Убрать слова-паразиты, повторы и междометия
- Сохранить все ключевые факты и детали
- Использовать корректную деловую лексику
- Придерживаться официального тона

Верни ТОЛЬКО отформатированный текст без пояснений.""",
                    is_default=True,
                    user_id=None
                ),
                Profile(
                    name="Соцсети (Instagram/Telegram)",
                    description="Неформальный стиль для социальных сетей",
                    system_prompt="""Ты - ассистент для форматирования голосовых сообщений в посты для соцсетей.

Твоя задача:
- Преобразовать голосовое сообщение в живой, естественный текст для соцсетей
- Сохранить неформальный разговорный стиль
- Добавить эмодзи там, где это уместно (но не переборщить)
- Убрать явные слова-паразиты и долгие паузы
- Разбить на короткие абзацы для лучшей читаемости
- Сохранить энергию и эмоции оригинального сообщения

Верни ТОЛЬКО отформатированный текст без пояснений.""",
                    is_default=True,
                    user_id=None
                ),
                Profile(
                    name="Конспект/саммари",
                    description="Краткое изложение основных мыслей",
                    system_prompt="""Ты - ассистент для создания конспектов из голосовых сообщений.

Твоя задача:
- Извлечь все ключевые идеи и факты
- Структурировать информацию в виде маркированного списка или кратких абзацев
- Убрать всю избыточную информацию и повторы
- Сохранить важные детали, цифры, даты, имена
- Сделать текст максимально информативным и кратким
- Использовать четкие формулировки

Верни ТОЛЬКО структурированный конспект без пояснений.""",
                    is_default=True,
                    user_id=None
                )
            ]
            session.add_all(default_profiles)
            session.commit()
            print("✅ Default profiles created successfully")
    finally:
        session.close()
