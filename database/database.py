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

    # Add indexes for analytics performance
    migrate_add_analytics_indexes(inspector)


def migrate_add_analytics_indexes(inspector=None):
    """Add indexes for analytics query performance"""
    if inspector is None:
        inspector = inspect(engine)

    # Get existing indexes to avoid duplicates
    existing_indexes = set()
    for table in ['usage_logs', 'users']:
        if table in inspector.get_table_names():
            for idx in inspector.get_indexes(table):
                existing_indexes.add(idx['name'])

    # Define indexes to add
    indexes_to_create = [
        ("idx_usage_logs_user_created",
         "CREATE INDEX idx_usage_logs_user_created ON usage_logs(user_id, created_at)"),
        ("idx_usage_logs_profile_created",
         "CREATE INDEX idx_usage_logs_profile_created ON usage_logs(profile_id, created_at)"),
        ("idx_usage_logs_success_created",
         "CREATE INDEX idx_usage_logs_success_created ON usage_logs(success, created_at)"),
        ("idx_users_last_activity",
         "CREATE INDEX idx_users_last_activity ON users(last_activity)"),
        ("idx_users_created_at",
         "CREATE INDEX idx_users_created_at ON users(created_at)")
    ]

    # Create missing indexes
    with engine.connect() as conn:
        for idx_name, idx_sql in indexes_to_create:
            if idx_name not in existing_indexes:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                    print(f"✅ Migration: Created index {idx_name}")
                except Exception as e:
                    print(f"⚠️ Migration: Could not create index {idx_name}: {e}")


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
