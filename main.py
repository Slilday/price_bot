import asyncio
import logging
import logging.handlers
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from config import config
from bot.handlers import user_commands, item_management, callbacks
from database.db import db
from services.monitor import run_price_monitor

def setup_logging():
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL_CONSOLE)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE_PATH, maxBytes=1*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(config.LOG_LEVEL_FILE)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    
    # Глушим лишние логи
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    # === 1. ИНИЦИАЛИЗАЦИЯ ===
    logger.info("📂 Подключаю базу данных...")
    await db.create_tables()
    logger.info("✅ База данных готова!")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(item_management.router)
    dp.include_router(user_commands.router)
    dp.include_router(callbacks.router)

    logger.info("🤖 Бот запущен и готов к работе!")
    
    # Запускаем мониторинг
    asyncio.create_task(run_price_monitor(bot))
    
    await bot.delete_webhook(drop_pending_updates=True)

    # === 2. ЦИКЛ ПОДКЛЮЧЕНИЯ ===
    reconnect_delays = [5, 15, 60, 300]
    attempt = 0
    
    while True:
        try:
            await dp.start_polling(bot)
            
        except TelegramNetworkError as e:
            logger.error(f"❌ Сбой сети Telegram: {e}")
            delay = reconnect_delays[min(attempt, len(reconnect_delays) - 1)]
            logger.info(f"🔄 Реконнект через {delay} сек...")
            await asyncio.sleep(delay)
            attempt += 1
            
        except Exception as e:
            logger.critical(f"❌ Ошибка в main: {e}", exc_info=True)
            await asyncio.sleep(10)
            attempt = 0

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")