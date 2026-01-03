from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from bot.states.profile_states import ProfileEditing
from bot.handlers.profiles import get_user_profiles
from bot.keyboards.inline import (
    get_profiles_keyboard,
    get_edit_field_keyboard,
    get_profile_management_keyboard
)
from database.database import Session
from database.models import User, Profile

router = Router()


@router.message(Command("edit"))
async def cmd_edit(message: Message):
    """Handle /edit command - show profiles for editing"""
    session = Session()
    try:
        all_profiles = get_user_profiles(session, message.from_user.id)

        if not all_profiles:
            await message.answer("❌ Профили не найдены")
            return

        keyboard = get_profiles_keyboard(all_profiles)
        await message.answer(
            "✏️ <b>Выберите профиль для редактирования:</b>\n\n"
            "⭐ - Стандартные профили (будет создана ваша копия)\n"
            "✏️ - Ваши профили",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        session.close()


@router.callback_query(F.data.startswith("edit_profile:"))
async def edit_profile_callback(callback: CallbackQuery):
    """Start editing a profile - show field selection"""
    profile_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        hint = ""
        if profile.is_default:
            hint = "\n\n💡 <i>Это стандартный профиль. При редактировании будет создана ваша персональная копия.</i>"

        keyboard = get_edit_field_keyboard(profile_id)
        await callback.message.edit_text(
            f"✏️ <b>Редактирование профиля:</b> {profile.name}\n\n"
            f"📋 Описание: {profile.description or 'Нет'}\n"
            f"🤖 Промпт: {profile.system_prompt[:100]}...{hint}\n\n"
            "Что хотите изменить?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()

    finally:
        session.close()


@router.callback_query(F.data.startswith("edit_field:"))
async def edit_field_callback(callback: CallbackQuery, state: FSMContext):
    """Handle field selection for editing"""
    parts = callback.data.split(":")
    profile_id = int(parts[1])
    field = parts[2]

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        # Save context
        await state.update_data(
            profile_id=profile_id,
            field=field,
            is_default=profile.is_default
        )

        field_names = {
            "name": ("название", profile.name, 100),
            "description": ("описание", profile.description or "", 500),
            "prompt": ("промпт", profile.system_prompt, None)
        }

        field_name, current_value, max_len = field_names[field]
        limit_hint = f" (максимум {max_len} символов)" if max_len else ""

        await callback.message.edit_text(
            f"✏️ <b>Изменение поля:</b> {field_name}\n\n"
            f"<b>Текущее значение:</b>\n<code>{current_value[:500]}</code>\n\n"
            f"Введите новое значение{limit_hint}:",
            parse_mode="HTML"
        )
        await state.set_state(ProfileEditing.entering_new_value)
        await callback.answer()

    finally:
        session.close()


@router.message(ProfileEditing.entering_new_value)
async def process_new_value(message: Message, state: FSMContext):
    """Process new field value with copy-on-write logic"""
    new_value = message.text.strip()
    data = await state.get_data()

    profile_id = data['profile_id']
    field = data['field']
    is_default = data['is_default']

    # Validate
    limits = {"name": 100, "description": 500, "prompt": None}
    max_len = limits.get(field)

    if max_len and len(new_value) > max_len:
        await message.answer(f"❌ Слишком длинное значение. Максимум {max_len} символов.")
        return

    if field == "prompt" and len(new_value) < 10:
        await message.answer("❌ Промпт слишком короткий. Минимум 10 символов.")
        return

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await message.answer("❌ Профиль не найден")
            await state.clear()
            return

        if is_default:
            # Copy-on-write: create user's copy of default profile
            new_profile = Profile(
                name=profile.name if field != "name" else new_value,
                description=profile.description if field != "description" else new_value,
                system_prompt=profile.system_prompt if field != "prompt" else new_value,
                is_default=False,
                user_id=message.from_user.id,
                parent_id=profile.id
            )
            session.add(new_profile)
            session.commit()

            # Update user's selected profile to the new copy
            user = session.query(User).filter_by(id=message.from_user.id).first()
            if user.selected_profile_id == profile_id:
                user.selected_profile_id = new_profile.id
                session.commit()

            await message.answer(
                f"✅ <b>Создана ваша копия профиля!</b>\n\n"
                f"📝 Название: {new_profile.name}\n"
                f"📋 Описание: {new_profile.description or 'Нет'}\n\n"
                "Теперь вы видите свою версию вместо стандартной.\n"
                "Используйте /profiles для выбора профиля.",
                parse_mode="HTML"
            )
        else:
            # Direct update for user's own profile
            if field == "name":
                profile.name = new_value
            elif field == "description":
                profile.description = new_value
            elif field == "prompt":
                profile.system_prompt = new_value

            session.commit()

            await message.answer(
                f"✅ <b>Профиль обновлён!</b>\n\n"
                f"📝 Название: {profile.name}\n"
                f"📋 Описание: {profile.description or 'Нет'}\n\n"
                "Используйте /profiles для выбора профиля.",
                parse_mode="HTML"
            )

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        session.close()
        await state.clear()


@router.callback_query(F.data.startswith("cancel_edit:"))
async def cancel_edit_callback(callback: CallbackQuery, state: FSMContext):
    """Cancel editing and return to profile management"""
    profile_id = int(callback.data.split(":")[1])
    await state.clear()

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if profile:
            is_default = profile.is_default
            is_copy = profile.parent_id is not None
            keyboard = get_profile_management_keyboard(profile_id, is_default=is_default, is_copy=is_copy)

            await callback.message.edit_text(
                f"✅ <b>Активный профиль:</b> {profile.name}\n\n"
                f"📝 <b>Описание:</b> {profile.description or 'Нет описания'}\n\n"
                "Теперь отправьте голосовое сообщение для обработки!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        await callback.answer("Редактирование отменено")

    finally:
        session.close()


@router.callback_query(F.data.startswith("reset_profile:"))
async def reset_profile_callback(callback: CallbackQuery):
    """Reset to original default profile (delete user's copy)"""
    profile_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        if not profile.parent_id:
            await callback.answer("❌ Это не копия профиля", show_alert=True)
            return

        # Check ownership
        if profile.user_id != callback.from_user.id:
            await callback.answer("❌ Это не ваш профиль", show_alert=True)
            return

        parent_id = profile.parent_id
        parent = session.query(Profile).filter_by(id=parent_id).first()

        # Update selected profile to parent if needed
        user = session.query(User).filter_by(id=callback.from_user.id).first()
        if user.selected_profile_id == profile_id:
            user.selected_profile_id = parent_id

        # Delete the copy
        session.delete(profile)
        session.commit()

        if parent:
            keyboard = get_profile_management_keyboard(parent_id, is_default=True, is_copy=False)
            await callback.message.edit_text(
                f"🔄 <b>Профиль сброшен к оригиналу!</b>\n\n"
                f"✅ <b>Активный профиль:</b> {parent.name}\n\n"
                f"📝 <b>Описание:</b> {parent.description or 'Нет описания'}\n\n"
                "Теперь отправьте голосовое сообщение для обработки!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        await callback.answer("Профиль сброшен к оригиналу")

    finally:
        session.close()


@router.callback_query(F.data.startswith("delete_profile:"))
async def delete_profile_callback(callback: CallbackQuery):
    """Delete user's custom profile"""
    profile_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        if profile.is_default:
            await callback.answer("❌ Нельзя удалить стандартный профиль", show_alert=True)
            return

        if profile.user_id != callback.from_user.id:
            await callback.answer("❌ Это не ваш профиль", show_alert=True)
            return

        profile_name = profile.name

        # Clear selected profile if it's being deleted
        user = session.query(User).filter_by(id=callback.from_user.id).first()
        if user.selected_profile_id == profile_id:
            user.selected_profile_id = None

        session.delete(profile)
        session.commit()

        # Show profiles list
        all_profiles = get_user_profiles(session, callback.from_user.id)
        keyboard = get_profiles_keyboard(all_profiles)

        await callback.message.edit_text(
            f"🗑 <b>Профиль '{profile_name}' удалён</b>\n\n"
            "📋 <b>Выберите профиль форматирования:</b>\n\n"
            "⭐ - Стандартные профили\n"
            "✏️ - Ваши профили",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer("Профиль удалён")

    finally:
        session.close()
