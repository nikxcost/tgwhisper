from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.database import Session
from database.models import UsageLog, Profile
from datetime import datetime

router = Router()

@router.message(Command("history"))
async def cmd_history(message: Message):
    """Show user's processing history"""
    session = Session()
    try:
        # Get last 5 successful logs
        logs = session.query(UsageLog).filter_by(
            user_id=message.from_user.id,
            success=True
        ).order_by(UsageLog.created_at.desc()).limit(5).all()

        if not logs:
            await message.answer("📭 История обработок пуста.\n\nОтправьте голосовое сообщение, чтобы начать!")
            return

        text = "📜 <b>История последних обработок:</b>\n\n"

        for i, log in enumerate(logs, 1):
            profile = session.query(Profile).filter_by(id=log.profile_id).first()
            profile_name = profile.name if profile else "Неизвестный профиль"

            # Format date
            date_str = log.created_at.strftime("%d.%m.%Y %H:%M")

            # Get preview (first 80 characters)
            preview = log.formatted_text[:80] + "..." if log.formatted_text and len(log.formatted_text) > 80 else log.formatted_text or "—"

            text += f"{i}. <b>{profile_name}</b>\n"
            text += f"   📅 {date_str}\n"
            text += f"   🎙 {log.audio_duration_seconds}с • ⚡️ {log.processing_time_seconds}с\n"
            text += f"   📄 {preview}\n\n"

        # Add buttons to view full texts
        keyboard = []
        for i, log in enumerate(logs, 1):
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📄 Показать полный текст #{i}",
                    callback_data=f"show_log:{log.id}"
                )
            ])

        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=markup, parse_mode="HTML")

    finally:
        session.close()


@router.callback_query(F.data.startswith("show_log:"))
async def show_full_log(callback: CallbackQuery):
    """Show full text of a specific log entry"""
    log_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        log = session.query(UsageLog).filter_by(id=log_id).first()

        if not log or log.user_id != callback.from_user.id:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return

        profile = session.query(Profile).filter_by(id=log.profile_id).first()
        profile_name = profile.name if profile else "Неизвестный профиль"
        date_str = log.created_at.strftime("%d.%m.%Y %H:%M")

        text = f"📝 <b>Профиль:</b> {profile_name}\n"
        text += f"📅 <b>Дата:</b> {date_str}\n\n"
        text += f"<blockquote>{log.formatted_text}</blockquote>"

        await callback.message.answer(text, parse_mode="HTML")
        await callback.answer()

    finally:
        session.close()
