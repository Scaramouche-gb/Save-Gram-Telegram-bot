import logging
import os
import asyncio
import subprocess

logger = logging.getLogger(__name__)

# Ограничиваем количество одновременных загрузок для защиты от блокировок
pinterest_semaphore = asyncio.Semaphore(2)

async def download_pinterest_media(url: str, user_id: int) -> str | None:
    async with pinterest_semaphore:
        # Путь для скачивания
        download_dir = f"downloads/pin_{user_id}"
        os.makedirs(download_dir, exist_ok=True)
        
        try:
            # Небольшая задержка перед скачиванием
            await asyncio.sleep(1)

            # Запускаем gallery-dl через subprocess (это надежнее для управления путями)
            # Параметр -d указывает директорию, --clear-cache помогает при ошибках 403
            process = await asyncio.create_subprocess_exec(
                'gallery-dl',
                '-d', download_dir,
                url,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()

            # Ищем скачанный файл в папке
            downloaded_file = None
            for root, dirs, files in os.walk(download_dir):
                for file in files:
                    # Берем первый попавшийся файл (картинку или видео)
                    downloaded_file = os.path.join(root, file)
                    break
                if downloaded_file:
                    break # exit outer loop once file is found
            
            if downloaded_file and os.path.exists(downloaded_file):
                logger.info(f"Pinterest медиа успешно скачано: {downloaded_file}")
                return downloaded_file
            else:
                logger.error(f"Gallery-dl error: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Ошибка Pinterest при скачивании медиа: {e}")
            return None
