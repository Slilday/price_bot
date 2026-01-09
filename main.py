import asyncio
import logging
import logging.handlers
from aiogram import Bot, Dispatcher
from config import config
from bot.handlers import user_commands, item_management, callbacks
from database.db import db
from services.monitor import run_price_monitor

def setup_logging():
    """Настраивает логирование в файл и консоль."""
    # Создаем основной логгер
    log = logging.getLogger()
    log.setLevel(logging.DEBUG) # Минимальный уровень, чтобы ловить все сообщения

    # Форматтер для сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # === Обработчик для консоли ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL_CONSOLE)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    # === Обработчик для файла ===
    # RotatingFileHandler автоматически создает новый файл, когда старый достигает 1 МБ
    # backupCount=5 значит, что будет храниться 5 старых лог-файлов
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE_PATH,
        maxBytes=1 * 1024 * 1024, # 1 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(config.LOG_LEVEL_FILE)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    
    # Отключаем слишком "болтливые" логгеры aiogram и http-клиентов
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    print("📝 Логирование настроено!")


async def main():
    # Настраиваем логирование ПЕРЕД ВСЕМ ОСТАЛЬНЫМ
    setup_logging()
    
    # Получаем корневой логгер
    logger = logging.getLogger(__name__)

    logger.info("📂 Подключаю базу данных...")
    await db.create_tables()
    logger.info("✅ База данных готова!")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(item_management.router)
    dp.include_router(user_commands.router)
    dp.include_router(callbacks.router)

    logger.info("🤖 Бот запущен и готов к работе!")
    
    # Запускаем фоновый мониторинг
    asyncio.create_task(run_price_monitor(bot))
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен")
    except Exception as e:
        # Логируем критические ошибки при запуске
        logging.critical(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)