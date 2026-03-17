import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = os.getenv("ADMIN_ID")
    DB_NAME = "prices.db"

    LOG_FILE_PATH = "bot.log"
    LOG_LEVEL_CONSOLE = "INFO" 
    LOG_LEVEL_FILE = "DEBUG"   

    if not BOT_TOKEN:
        raise ValueError("❌ В файле .env не найден BOT_TOKEN!")

config = Config()