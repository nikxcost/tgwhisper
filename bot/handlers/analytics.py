"""
Analytics Handler for TGWhisper Bot

Admin-only command for exporting product analytics metrics.
Provides DAU/MAU, conversion, retention, profile popularity,
performance metrics, error rates, and usage patterns.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)
from datetime import date

from config import config
from database.database import Session
from services.analytics_service import AnalyticsService
from utils.logger import logger

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user has admin privileges"""
    return user_id in config.ADMIN_USER_IDS


def get_analytics_keyboard() -> InlineKeyboardMarkup:
    """Generate inline keyboard with time period options"""
    keyboard = [
        [
            InlineKeyboardButton(text="7 дней", callback_data="analytics:7"),
            InlineKeyboardButton(text="30 дней", callback_data="analytics:30")
        ],
        [
            InlineKeyboardButton(text="90 дней", callback_data="analytics:90"),
            InlineKeyboardButton(text="Всё время", callback_data="analytics:all")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("analytics"))
async def cmd_analytics(message: Message):
    """Handle /analytics command - show period selection"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён. Эта команда доступна только администраторам.")
        logger.warning(f"Unauthorized analytics access attempt by user {message.from_user.id}")
        return

    # Get quick stats preview
    session = Session()
    try:
        analytics = AnalyticsService(session)
        dau = analytics.get_dau(date.today())
        mau = analytics.get_mau(30)
        total_users = analytics.get_total_users()
        error_rates = analytics.get_error_rates(30)

        text = (
            "<b>📊 Аналитика бота</b>\n\n"
            f"<b>Краткая сводка (30 дней):</b>\n"
            f"👥 DAU (сегодня): {dau}\n"
            f"👥 MAU: {mau}\n"
            f"📝 Всего пользователей: {total_users}\n"
            f"✅ Success rate: {error_rates['success_rate']}%\n"
            f"📨 Всего запросов: {error_rates['total_requests']}\n\n"
            "<b>Выберите период для полного отчёта:</b>"
        )

        await message.answer(
            text,
            reply_markup=get_analytics_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error getting analytics preview: {e}")
        await message.answer(
            "📊 <b>Аналитика бота</b>\n\n"
            "Выберите период для экспорта отчёта:",
            reply_markup=get_analytics_keyboard(),
            parse_mode="HTML"
        )
    finally:
        session.close()


@router.callback_query(F.data.startswith("analytics:"))
async def export_analytics_callback(callback: CallbackQuery):
    """Handle period selection and generate export files"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        logger.warning(f"Unauthorized analytics callback by user {callback.from_user.id}")
        return

    # Parse period
    period_str = callback.data.split(":")[1]
    days = None if period_str == "all" else int(period_str)

    period_label = "за всё время" if days is None else f"за {days} дней"

    # Show processing message
    await callback.answer()
    processing_msg = await callback.message.answer(f"⏳ Генерирую отчёт {period_label}...")

    session = Session()
    try:
        analytics = AnalyticsService(session)

        # Generate exports
        csv_zip = analytics.export_to_csv(days)
        json_data = analytics.export_to_json(days)

        # Generate filenames
        filename_suffix = f"{days}days" if days else "all_time"
        date_str = date.today().isoformat()

        # Send CSV ZIP
        await callback.message.answer_document(
            BufferedInputFile(
                csv_zip.getvalue(),
                filename=f"analytics_{filename_suffix}_{date_str}.zip"
            ),
            caption=f"📊 Аналитика {period_label} (CSV)"
        )

        # Send JSON
        await callback.message.answer_document(
            BufferedInputFile(
                json_data,
                filename=f"analytics_{filename_suffix}_{date_str}.json"
            ),
            caption=f"📊 Аналитика {period_label} (JSON)"
        )

        # Delete processing message
        await processing_msg.delete()

        # Send success message with return button
        await callback.message.answer(
            "✅ Отчёты готовы!\n\n"
            "Выберите другой период или закройте меню:",
            reply_markup=get_analytics_keyboard()
        )

        logger.info(f"Analytics exported by admin {callback.from_user.id}, period: {period_str}")

    except Exception as e:
        logger.error(f"Error generating analytics export: {e}")
        await processing_msg.edit_text(
            f"❌ Ошибка при генерации отчёта: {str(e)}\n\n"
            "Попробуйте ещё раз или выберите другой период.",
            reply_markup=get_analytics_keyboard()
        )
    finally:
        session.close()
