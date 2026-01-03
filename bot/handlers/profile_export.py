from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from database.database import Session
from database.models import Profile
from config import config
import json

router = Router()

@router.callback_query(F.data.startswith("export_profile:"))
async def export_profile(callback: CallbackQuery):
    """Export profile to JSON file"""
    profile_id = int(callback.data.split(":")[1])

    session = Session()
    try:
        profile = session.query(Profile).filter_by(id=profile_id).first()

        if not profile:
            await callback.answer("❌ Профиль не найден", show_alert=True)
            return

        # Check if user owns this profile (can't export default profiles created by others)
        if profile.is_default and profile.user_id is None:
            # Allow exporting system default profiles
            pass
        elif profile.user_id != callback.from_user.id:
            await callback.answer("❌ Вы не можете экспортировать чужой профиль", show_alert=True)
            return

        # Create JSON
        profile_data = {
            "name": profile.name,
            "description": profile.description,
            "system_prompt": profile.system_prompt,
            "version": "1.0"
        }

        json_str = json.dumps(profile_data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')

        # Send as file
        filename = f"profile_{profile.name.replace(' ', '_')}.json"
        file = BufferedInputFile(json_bytes, filename=filename)

        await callback.message.answer_document(
            document=file,
            caption=f"📤 <b>Профиль экспортирован:</b> {profile.name}\n\n"
                    "Отправьте этот файл боту для импорта.",
            parse_mode="HTML"
        )
        await callback.answer("✅ Профиль экспортирован")

    finally:
        session.close()


@router.message(F.document)
async def import_profile(message: Message):
    """Import profile from JSON file"""
    # Check if it's a JSON file
    if not message.document.file_name.endswith('.json'):
        return  # Not a profile file, ignore

    session = Session()
    try:
        # Download file
        file = await message.bot.get_file(message.document.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        json_str = file_bytes.read().decode('utf-8')

        # Parse JSON
        try:
            profile_data = json.loads(json_str)
        except json.JSONDecodeError:
            await message.answer("❌ Неверный формат файла")
            return

        # Validate required fields
        required_fields = ["name", "description", "system_prompt"]
        if not all(field in profile_data for field in required_fields):
            await message.answer("❌ В файле отсутствуют обязательные поля")
            return

        # Check profile limit
        custom_count = session.query(Profile).filter_by(
            user_id=message.from_user.id,
            is_default=False
        ).count()

        if custom_count >= config.MAX_CUSTOM_PROFILES:
            await message.answer(
                f"⚠️ Достигнут лимит пользовательских профилей ({config.MAX_CUSTOM_PROFILES}).\n"
                "Удалите ненужные профили перед импортом."
            )
            return

        # Create new profile
        profile = Profile(
            name=profile_data["name"],
            description=profile_data["description"],
            system_prompt=profile_data["system_prompt"],
            is_default=False,
            user_id=message.from_user.id
        )
        session.add(profile)
        session.commit()

        await message.answer(
            f"✅ <b>Профиль импортирован!</b>\n\n"
            f"📝 Название: {profile.name}\n"
            f"📄 Описание: {profile.description}\n\n"
            "Используйте /profiles для выбора этого профиля.",
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка при импорте: {str(e)}")
    finally:
        session.close()
