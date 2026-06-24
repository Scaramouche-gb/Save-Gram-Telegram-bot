import os
import logging
from aiogram import Router, types, F
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext

from services.ydl_service import ydl_service
from core.config import config

router = Router()
logger = logging.getLogger(__name__)

# limits Telegram
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB

def get_format_keyboard():
    """Inline keyboard for quality selection."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🎥 Видео 720p", callback_data="yt_format:720")],
            [types.InlineKeyboardButton(text="📱 Видео 480p", callback_data="yt_format:480")],
            [types.InlineKeyboardButton(text="🎵 Аудио (MP3)", callback_data="yt_format:mp3")]
        ]
    )

async def show_format_menu(message: types.Message):
    """Displays the format selection menu."""
    await message.reply(
        "🎬 **YouTube:** Выберите качество скачивания:",
        reply_markup=get_format_keyboard(),
        parse_mode="Markdown"
    )

async def download_and_send_video(message: types.Message, state: FSMContext, url: str, selected_format: str):
    """
    The basic logic of downloading and uploading YouTube content.
    """
    # We generate options depending on the user's choice
    if selected_format == 'mp3':
        yt_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        # For video, we limit the frame height (720 or 480)
        yt_opts = {
            'format': f'bestvideo[height<={selected_format}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        }

    try:
        file_path = await ydl_service.download_video(url, yt_opts, platform='youtube')
        if selected_format == 'mp3':
            # ydl_service might return the original file path before extension change,
            # so we explicitly check for the .mp3 version
            base_file_name, _ = os.path.splitext(file_path)
            final_file_path = f"{base_file_name}.mp3"
        else:
            final_file_path = file_path # For video, the path from ydl_service should be correct

        logger.info(f"Проверка файла по пути: {final_file_path}")

        if final_file_path and os.path.exists(final_file_path):
            file_size = os.path.getsize(final_file_path)
            bot_link = f"https://t.me/{config.BOT_USERNAME.lstrip('@')}"
            caption = f"[Скачать любую песню или видео🎧]({bot_link})"
            video_file = FSInputFile(final_file_path)
            

            # 1. If this is audio
            if selected_format == 'mp3':
                await message.answer_audio(audio=video_file, caption=caption, parse_mode="MarkdownV2")
            
            # 2. If the video is small (up to 50 MB), we send it as a video.
            elif file_size <= MAX_VIDEO_SIZE:
                await message.answer_video(video=video_file, caption=caption, parse_mode="MarkdownV2")
            
            # 3. If the video is large, we send it as a document.
            else:
                await message.answer_document(document=video_file, caption=caption, parse_mode="MarkdownV2")

            # We clean up after ourselves
            os.remove(final_file_path)
            logger.info(f"YouTube файл отправлен и удален: {final_file_path}")
        else:
            await message.answer("❌ Ошибка: Не удалось загрузить видео с YouTube.")
            logger.info(f"Youtube не получилось отправить файл пользователю")

    except Exception as e:
        logger.error(f"Ошибка в YouTube хендлере: {e}")
        await message.answer("❌ Произошла ошибка при обработке YouTube ссылки.")