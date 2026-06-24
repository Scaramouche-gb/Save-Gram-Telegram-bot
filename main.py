import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# import our settings and logger
from core.config import config
from core.logger import setup_logger
from middlewares.subscribe import SubscribeMiddleware

# Import routers from the handlers folder
from handlers import common, downloader, callbacks, pinterest
from services.ydl_service import ydl_service

async def main():
    # 1. Launching the logger
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Бот запускается...")

    # 2. Initializing the bot and dispatcher
    bot = Bot(token=config.BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Register Middleware 
    dp.message.outer_middleware(SubscribeMiddleware())

    # 4. Connecting modules (routers)
    dp.include_routers(
        common.router,
        callbacks.router,
        pinterest.router, # Specific Pinterest handler
        downloader.router  # This one is always at the end because it catches all the links
    )

    # 5. start polling
    logger.info("Бот успешно запущен и готов к работе!")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        # Start the ydl worker queue in the background
        asyncio.create_task(ydl_service.worker())
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Критическая ошибка при работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен вручную")