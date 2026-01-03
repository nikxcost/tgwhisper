from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.database import Session
from database.models import User, Profile
from bot.keyboards.inline import get_profiles_keyboard, get_profile_management_keyboard

router = Router()


def get_user_profiles(session, user_id: int) -> list[Profile]:
    """Get profiles for user with copy-on-write logic"""
    default_profiles = session.query(Profile).filter_by(is_default=True).all()
    user_profiles = session.query(Profile).filter_by(
        user_id=user_id,
        is_default=False
    ).all()

    # Get parent_ids of user's copies
    user_copies_parent_ids = {p.parent_id for p in user_profiles if p.parent_id}

    # Filter out defaults that have user copies
    visible_defaults = [p for p in default_profiles if p.id not in user_copies_parent_ids]

    return visible_defaults + user_profiles


@router.message(Command("profiles"))
async def cmd_profiles(message: Message):
    """Handle /profiles command"""
    session = Session()
    try:
        all_profiles = get_user_profiles(session, message.from_user.id)

        if not all_profiles:
            await message.answer("❌ Профили не найдены")
            return

        keyboard = get_profiles_keyboard(all_profiles)
        await message.answer(
            "📋 <b>Выберите профиль форматирования:</b>\n\n"
            "⭐ - Стандартные профили\n"
            "✏️ - Ваши профили",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    finally:
        session.close()


@router.callback_query(F.data.startswith("select_profile:"))
async def select_profile_callback(callback: CallbackQuery):
    """Handle profile selection"""
    profile_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        user = session.query(User).filter_by(id=callback.from_user.id).first()
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        # Update user's selected profile
        user.selected_profile_id = profile_id
        session.commit()

        # Determine profile type for keyboard
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
        await callback.answer()

    finally:
        session.close()


@router.callback_query(F.data == "back_to_profiles")
async def back_to_profiles_callback(callback: CallbackQuery):
    """Handle back to profiles list"""
    session = Session()
    try:
        all_profiles = get_user_profiles(session, callback.from_user.id)
        keyboard = get_profiles_keyboard(all_profiles)

        await callback.message.edit_text(
            "📋 <b>Выберите профиль форматирования:</b>\n\n"
            "⭐ - Стандартные профили\n"
            "✏️ - Ваши профили",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
    finally:
        session.close()


@router.callback_query(F.data.startswith("profiles_page:"))
async def profiles_page_callback(callback: CallbackQuery):
    """Handle pagination"""
    page = int(callback.data.split(":")[1])

    session = Session()
    try:
        all_profiles = get_user_profiles(session, callback.from_user.id)
        keyboard = get_profiles_keyboard(all_profiles, page=page)

        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()

    finally:
        session.close()
