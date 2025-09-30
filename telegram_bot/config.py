#!/usr/bin/env python3

"""
Конфигурация бота - централизованное место для всех настроек
"""

import os
import logging
from pathlib import Path

# Конфигурация путей
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
SHARED_ENV_PATH = PROJECT_ROOT / '.env'

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv(SHARED_ENV_PATH)
except ImportError:
    os.system(f"{os.sys.executable} -m pip install python-dotenv --break-system-packages")
    from dotenv import load_dotenv
    load_dotenv(SHARED_ENV_PATH)

class BotConfig:
    """Центральная конфигурация бота"""

    # Telegram API
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # База данных
    DATABASE_PATH = PROJECT_ROOT / 'shared_database.db'

    # API
    API_BASE_URL = 'http://127.0.0.1:8000'

    # Процессы
    LOCK_FILE_NAME = 'telegram_bot.lock'
    MAX_STARTUP_RETRIES = 3
    RETRY_DELAY_SECONDS = 15

    # Логирование
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    @classmethod
    def get_lock_file_path(cls) -> Path:
        """Получить путь к файлу блокировки в зависимости от ОС"""
        if os.name == 'nt':  # Windows
            temp_dir = Path(os.environ.get('TEMP', Path.home() / 'AppData' / 'Local' / 'Temp'))
        else:  # Unix/Linux
            temp_dir = Path('/tmp')

        return temp_dir / cls.LOCK_FILE_NAME

    @classmethod
    def validate_config(cls) -> bool:
        """Проверить корректность конфигурации"""
        if not cls.BOT_TOKEN:
            print("❌ BOT_TOKEN не найден в переменных окружения")
            return False

        if not cls.DATABASE_PATH.exists():
            print(f"❌ База данных не найдена: {cls.DATABASE_PATH}")
            return False

        return True

    @classmethod
    def setup_logging(cls):
        """Настроить логирование"""
        logging.basicConfig(
            format=cls.LOG_FORMAT,
            level=cls.LOG_LEVEL,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(BASE_DIR / 'bot.log', encoding='utf-8')
            ]
        )

# Глобальный логгер
logger = logging.getLogger(__name__)