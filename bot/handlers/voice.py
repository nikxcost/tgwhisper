from aiogram import Router, F
from aiogram.types import Message
from services.whisper_service import transcribe_voice
from services.llm_service import format_text
from database.database import Session
from database.models import User, UsageLog
import time
from io import BytesIO

router = Router()

@router.message(F.voice)
async def handle_voice(message: Message):
    """Handle incoming voice messages"""
    session = Session()
    processing_msg = await message.answer("🎧 Обрабатываю голосовое сообщение...")

    start_time = time.time()
    success = True
    error_msg = None

    try:
        # 1. Get user and their selected profile
        user = session.query(User).filter_by(id=message.from_user.id).first()
        if not user or not user.selected_profile_id:
            await processing_msg.edit_text(
                "⚠️ Сначала выберите профиль форматирования.\n"
                "Используйте /profiles для выбора."
            )
            return

        profile = user.selected_profile

        # 2. Download voice file
        await processing_msg.edit_text("⬇️ Загружаю аудио...")
        file = await message.bot.get_file(message.voice.file_id)
        voice_bytes = await message.bot.download_file(file.file_path)

        # Convert to BytesIO
        voice_file = BytesIO(voice_bytes.read())
        voice_file.seek(0)

        # 3. Transcribe audio
        await processing_msg.edit_text("🎤 Распознаю речь...")
        transcribed_text = await transcribe_voice(voice_file)

        if not transcribed_text or len(transcribed_text.strip()) == 0:
            await processing_msg.edit_text("❌ Не удалось распознать речь в аудио.")
            return

        # 4. Format with LLM
        await processing_msg.edit_text("✨ Форматирую текст...")
        formatted_text = await format_text(transcribed_text, profile.system_prompt)

        # 5. Send formatted result as quote
        await message.answer(
            f"📝 <b>Профиль:</b> {profile.name}\n\n"
            f"<blockquote>{formatted_text}</blockquote>",
            parse_mode="HTML"
        )

        await processing_msg.delete()

        # Log usage
        log = UsageLog(
            user_id=user.id,
            profile_id=profile.id,
            audio_duration_seconds=message.voice.duration,
            transcription_length=len(transcribed_text),
            formatted_length=len(formatted_text),
            formatted_text=formatted_text,
            processing_time_seconds=int(time.time() - start_time),
            success=True
        )
        session.add(log)
        session.commit()

    except Exception as e:
        success = False
        error_msg = str(e)
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при обработке:\n<code>{str(e)}</code>",
            parse_mode="HTML"
        )

        # Log error
        log = UsageLog(
            user_id=message.from_user.id,
            profile_id=user.selected_profile_id if user else None,
            audio_duration_seconds=message.voice.duration if message.voice else None,
            processing_time_seconds=int(time.time() - start_time),
            success=False,
            error_message=error_msg
        )
        session.add(log)
        session.commit()

    finally:
        session.close()
