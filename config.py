import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = os.getenv("ADMIN_ID")
    DB_NAME = "prices.db"

    # === НАСТРОЙКИ ЛОГИРОВАНИЯ ===
    LOG_FILE_PATH = "bot.log"
    LOG_LEVEL_CONSOLE = "INFO"  # Уровень для вывода в консоль
    LOG_LEVEL_FILE = "DEBUG"    # Уровень для записи в файл
    # ============================

    if not BOT_TOKEN:
        raise ValueError("❌ В файле .env не найден BOT_TOKEN!")

config = Config()