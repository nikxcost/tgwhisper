from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from bot.states.profile_states import ProfileCreation
from database.database import Session
from database.models import User, Profile
from config import config

router = Router()

@router.callback_query(F.data == "create_profile")
async def start_profile_creation(callback: CallbackQuery, state: FSMContext):
    """Start the profile creation flow"""
    from utils.logger import logger
    logger.info(f"User {callback.from_user.id} started profile creation")

    session = Session()
    user = session.query(User).filter_by(id=callback.from_user.id).first()

    # Check limit
    custom_count = session.query(Profile).filter_by(
        user_id=user.id,
        is_default=False
    ).count()

    if custom_count >= config.MAX_CUSTOM_PROFILES:
        await callback.message.answer(
            f"⚠️ Достигнут лимит пользовательских профилей ({config.MAX_CUSTOM_PROFILES}).\n"
            "Удалите ненужные профили перед созданием новых."
        )
        await callback.answer()
        session.close()
        return

    session.close()

    await callback.message.answer(
        "📝 <b>Создание нового профиля</b>\n\n"
        "Введите название профиля (например: 'Рабочие заметки'):",
        parse_mode="HTML"
    )
    await state.set_state(ProfileCreation.entering_name)
    await callback.answer()

@router.message(ProfileCreation.entering_name)
async def process_profile_name(message: Message, state: FSMContext):
    """Process profile name input"""
    from utils.logger import logger
    current_state = await state.get_state()
    logger.info(f"process_profile_name called. Current state: {current_state}, user: {message.from_user.id}, text: {message.text}")

    name = message.text.strip()

    if len(name) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return

    await state.update_data(name=name)

    await message.answer(
        f"✅ Название: <b>{name}</b>\n\n"
        "Теперь введите описание профиля (что он делает):",
        parse_mode="HTML"
    )
    await state.set_state(ProfileCreation.entering_description)
    new_state = await state.get_state()
    logger.info(f"State changed from {current_state} to {new_state}")

@router.message(ProfileCreation.entering_description)
async def process_profile_description(message: Message, state: FSMContext):
    """Process profile description input"""
    from utils.logger import logger
    current_state = await state.get_state()
    logger.info(f"process_profile_description called. Current state: {current_state}, text: {message.text[:50]}")

    description = message.text.strip()

    if len(description) > 500:
        await message.answer("❌ Описание слишком длинное. Максимум 500 символов.")
        return

    await state.update_data(description=description)
    await message.answer(
        "✅ Описание сохранено.\n\n"
        "Теперь введите системный промпт для LLM.\n"
        "Это инструкция, как форматировать текст:\n\n"
        "<i>Пример: 'Ты - ассистент. Преобразуй голосовое сообщение в краткий список задач. "
        "Используй маркированный список. Убери лишние слова.'</i>",
        parse_mode="HTML"
    )
    await state.set_state(ProfileCreation.entering_prompt)
    new_state = await state.get_state()
    logger.info(f"State changed from {current_state} to {new_state}")

@router.message(ProfileCreation.entering_prompt)
async def process_profile_prompt(message: Message, state: FSMContext):
    """Process system prompt and create profile"""
    from utils.logger import logger
    current_state = await state.get_state()
    logger.info(f"process_profile_prompt called. Current state: {current_state}, text: {message.text[:50]}")

    prompt = message.text.strip()

    if len(prompt) < 10:
        await message.answer("❌ Промпт слишком короткий. Минимум 10 символов.")
        return

    # Get all data
    data = await state.get_data()
    name = data['name']
    description = data['description']

    # Create profile
    session = Session()
    try:
        profile = Profile(
            name=name,
            description=description,
            system_prompt=prompt,
            is_default=False,
            user_id=message.from_user.id
        )
        session.add(profile)
        session.commit()

        await message.answer(
            f"✅ <b>Профиль создан!</b>\n\n"
            f"📝 Название: {name}\n"
            f"📄 Описание: {description}\n\n"
            "Используйте /profiles для выбора этого профиля.",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при создании профиля: {str(e)}")
    finally:
        session.close()
        await state.clear()
