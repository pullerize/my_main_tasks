#!/usr/bin/env python3

"""
8Bit Task Management System - Telegram Bot
Полнофункциональный Telegram бот для системы управления задачами
"""

import os
import sys
import platform
import asyncio
import logging
import sqlite3
import subprocess
import atexit
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

# Кроссплатформенные импорты для блокировки
try:
    import fcntl  # Unix/Linux
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    try:
        import msvcrt  # Windows
        HAS_MSVCRT = True
    except ImportError:
        HAS_MSVCRT = False

# Подключение к Telegram API
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    os.system(f"{sys.executable} -m pip install nest_asyncio --break-system-packages")
    import nest_asyncio
    nest_asyncio.apply()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.constants import UpdateType
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Импортируем обработчики администратора, обычных пользователей и расходов
from admin_task_handlers import AdminTaskHandlers
from user_task_handlers import UserTaskHandlers
from expense_handlers import ExpenseHandlers

# Конфигурация
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    os.system(f"{sys.executable} -m pip install python-dotenv --break-system-packages")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_PATH = os.getenv('SQLITE_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared_database.db'))

# API URL: в Docker используем имя контейнера, локально - localhost
API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000')
if os.path.exists('/.dockerenv'):
    # Внутри Docker контейнера
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000')
else:
    # Локальная разработка
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Уменьшаем уровень логирования для httpx и telegram (убираем HTTP запросы из логов)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

# Создаём фильтр для игнорирования ошибок 409 Conflict в логах
class ConflictErrorFilter(logging.Filter):
    def filter(self, record):
        # Игнорируем ошибки 409 Conflict - они не критичны
        return '409' not in record.getMessage() and 'Conflict' not in record.getMessage()

# Применяем фильтр к telegram.ext.Updater
updater_logger = logging.getLogger('telegram.ext.Updater')
updater_logger.addFilter(ConflictErrorFilter())

# Защита от множественного запуска
if platform.system() == 'Windows':
    LOCK_FILE = os.path.join(os.environ.get('TEMP', ''), 'telegram_bot.lock')
else:
    LOCK_FILE = '/tmp/telegram_bot.lock'

lock_file_handle = None

def acquire_lock():
    """Получить блокировку для предотвращения множественного запуска (кроссплатформенно)"""
    global lock_file_handle

    # Сначала проверим, не существует ли уже файл блокировки
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = f.read().strip()
                if pid.isdigit():
                    # Проверим, существует ли процесс с таким PID
                    if is_process_running(int(pid)):
                        return False
                    else:
                        # Процесс не существует, удаляем старый lock файл
                        os.remove(LOCK_FILE)
        except (IOError, OSError, ValueError):
            # Если не можем прочитать файл, удаляем его
            try:
                os.remove(LOCK_FILE)
            except:
                pass

    try:
        # Создаем lock файл
        lock_file_handle = open(LOCK_FILE, 'w')

        if HAS_FCNTL:  # Unix/Linux
            import fcntl
            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif HAS_MSVCRT:  # Windows
            import msvcrt
            # На Windows используем эксклюзивную блокировку файла
            msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)

        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()

        # Автоматически освободить блокировку при выходе
        atexit.register(release_lock)
        return True

    except (IOError, OSError):
        if lock_file_handle:
            try:
                lock_file_handle.close()
            except:
                pass
            lock_file_handle = None
        return False

def is_process_running(pid):
    """Проверить, запущен ли процесс с данным PID"""
    try:
        if platform.system() == 'Windows':
            import subprocess
            try:
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                                      capture_output=True, text=True, check=False)
                # Проверяем что в выводе есть строка с нашим PID и python
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if str(pid) in line and ('python' in line.lower() or 'bot.py' in line.lower()):
                        return True
                return False
            except (subprocess.CalledProcessError, Exception):
                return False
        else:
            os.kill(pid, 0)  # Не убивает процесс, только проверяет существование
            return True
    except (OSError, ProcessLookupError):
        return False

def release_lock():
    """Освободить блокировку"""
    global lock_file_handle
    try:
        if lock_file_handle:
            if HAS_FCNTL:
                import fcntl
                fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
            elif HAS_MSVCRT:
                import msvcrt
                msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_UNLCK, 1)

            lock_file_handle.close()
            lock_file_handle = None

        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except (IOError, OSError):
        pass

# Проверяем блокировку при импорте модуля
# Можно запустить с флагом --force для принудительного запуска
force_start = '--force' in sys.argv
if force_start:
    print("⚠️  Принудительный запуск бота...")
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except:
        pass

if not acquire_lock():
    print("❌ Другой экземпляр бота уже запущен!")
    print("🔄 Дождитесь его завершения или завершите процесс принудительно.")
    print("💡 Или используйте: python bot.py --force")
    sys.exit(1)

class TelegramBot:
    """Главный класс Telegram бота"""

    def __init__(self, token: str):
        self.token = token
        self.app = None
        self.API_BASE_URL = API_BASE_URL  # Добавляем API_BASE_URL как атрибут

        # Connection pool для SQLite (отложенная инициализация)
        self._connection_pool = []
        self._pool_size = 5
        self._pool_lock = threading.Lock()

        logger.info("✅ Connection pool инициализирован")

        self.admin_handlers = AdminTaskHandlers(self)
        self.user_task_handlers = UserTaskHandlers(self)
        self.expense_handlers = ExpenseHandlers(self)

    def _execute_query(self, conn, query: str, params: tuple, return_id: bool = False):
        """
        Вспомогательная функция для выполнения SQL запросов
        с автоматическим определением типа БД (SQLite или PostgreSQL)

        Args:
            conn: Database connection
            query: SQL query string
            params: Query parameters
            return_id: If True, добавляет RETURNING id для PostgreSQL INSERT запросов
        """
        import os
        db_engine = os.getenv('DB_ENGINE', 'sqlite').lower()

        if db_engine == 'postgresql':
            # PostgreSQL: создаем курсор и используем %s для параметров
            cursor = conn.cursor()
            # Заменяем ? на %s для PostgreSQL
            pg_query = query.replace('?', '%s')
            # Заменяем boolean поля: 1/0 -> true/false для PostgreSQL
            pg_query = pg_query.replace('is_active = 1', 'is_active = true')
            pg_query = pg_query.replace('is_active = 0', 'is_active = false')
            pg_query = pg_query.replace('is_archived = 1', 'is_archived = true')
            pg_query = pg_query.replace('is_archived = 0', 'is_archived = false')
            pg_query = pg_query.replace('is_recurring = 1', 'is_recurring = true')
            pg_query = pg_query.replace('is_recurring = 0', 'is_recurring = false')

            # Для INSERT запросов в PostgreSQL добавляем RETURNING id
            if return_id and 'INSERT INTO' in pg_query.upper():
                pg_query = pg_query.rstrip().rstrip(';') + ' RETURNING id'

            cursor.execute(pg_query, params)
            return cursor
        else:
            # SQLite: используем execute напрямую с ?
            return conn.execute(query, params)

    def _create_connection(self):
        """Создать новое подключение к БД"""
        try:
            db_engine = os.getenv('DB_ENGINE', 'sqlite').lower()

            if db_engine == 'postgresql':
                # PostgreSQL подключение
                import psycopg2
                import psycopg2.extras

                conn_params = {
                    'host': os.getenv('POSTGRES_HOST', 'localhost'),
                    'port': os.getenv('POSTGRES_PORT', '5432'),
                    'database': os.getenv('POSTGRES_DB', '8bit_tasks'),
                    'user': os.getenv('POSTGRES_USER', '8bit_user'),
                    'password': os.getenv('POSTGRES_PASSWORD', ''),
                }

                logger.info(f"Попытка подключения к PostgreSQL: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
                conn = psycopg2.connect(**conn_params)
                # Используем RealDictCursor для совместимости со sqlite3.Row
                conn.cursor_factory = psycopg2.extras.RealDictCursor
                logger.info("✅ Подключение к PostgreSQL создано успешно")
                return conn
            else:
                # SQLite подключение
                logger.info(f"Попытка подключения к SQLite: {DATABASE_PATH}")
                conn = sqlite3.connect(
                    DATABASE_PATH,
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                logger.info("✅ Подключение к SQLite создано успешно")
                return conn

        except Exception as e:
            logger.error(f"Ошибка создания подключения к БД: {e}")
            return None

    def get_db_connection(self):
        """Получить подключение из пула"""
        with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
                # Проверяем жизнь соединения
                try:
                    conn.execute("SELECT 1")
                    return conn
                except:
                    # Соединение мертво, создаем новое
                    return self._create_connection()
            else:
                # Пул пуст, создаем новое соединение
                return self._create_connection()

    def return_db_connection(self, conn):
        """Вернуть подключение в пул"""
        if conn:
            with self._pool_lock:
                if len(self._connection_pool) < self._pool_size:
                    self._connection_pool.append(conn)
                else:
                    conn.close()

    def get_user_by_telegram_id(self, telegram_id: int, username: str = None):
        """Получение пользователя по Telegram ID или username через API"""
        try:
            import requests
            # Используем API вместо прямого доступа к БД для избежания проблем с SQLite на Windows FS
            response = requests.get(
                f'{API_BASE_URL}/users/by-telegram/{telegram_id}',
                params={'username': username} if username else {},
                timeout=5
            )

            if response.status_code == 200:
                user_dict = response.json()
                # Проверяем активность пользователя
                if user_dict.get('role') == 'inactive' or not user_dict.get('is_active', True):
                    return None
                return user_dict
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя через API: {e}")
            return None

    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Получение активных задач пользователя (только статус in_progress)"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = self._execute_query(conn, """
                SELECT t.*
                FROM tasks t
                WHERE t.executor_id = ? AND t.status = 'in_progress'
                ORDER BY t.created_at DESC
                LIMIT 10
            """, (user_id,))
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return tasks
        except Exception as e:
            logger.error(f"Ошибка получения задач: {e}")
            conn.close()
            return []

    def get_user_in_progress_tasks(self, user_id: int) -> List[Dict]:
        """Получение задач пользователя принятых в работу (статус in_progress)"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = self._execute_query(conn, """
                SELECT t.*
                FROM tasks t
                WHERE t.executor_id = ? AND t.status = 'in_progress'
                ORDER BY t.created_at DESC
                LIMIT 10
            """, (user_id,))
            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return tasks
        except Exception as e:
            logger.error(f"Ошибка получения задач в работе: {e}")
            conn.close()
            return []

    def get_user_projects(self, user_id: int) -> List[Dict]:
        """Получение проектов пользователя с активными задачами"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = self._execute_query(conn, """
                SELECT DISTINCT p.*
                FROM projects p
                INNER JOIN tasks t ON p.id = t.project_id
                WHERE t.executor_id = ? AND t.status = 'in_progress'
                ORDER BY p.created_at DESC
            """, (user_id,))
            projects = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return projects
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
            conn.close()
            return []

    def get_user_expenses(self, user_id: int) -> List[Dict]:
        """Получение расходов пользователя"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = self._execute_query(conn, """
                SELECT e.*, p.name as project_name
                FROM employee_expenses e
                LEFT JOIN projects p ON e.project_id = p.id
                WHERE e.employee_id = ?
                ORDER BY e.date DESC
                LIMIT 10
            """, (user_id,))
            expenses = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return expenses
        except Exception as e:
            logger.error(f"Ошибка получения расходов: {e}")
            conn.close()
            return []

    def require_auth(self, func):
        """Декоратор для проверки авторизации"""
        async def wrapper(update: Update, context):
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)

            # Если пользователь не найден, пытаемся автоматическую авторизацию
            if not db_user:
                success, message, api_user = await self.try_auto_authorize(
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name
                )

                if success:
                    # Перезапрашиваем пользователя из базы
                    db_user = self.get_user_by_telegram_id(user.id, user.username)

            if not db_user:
                # Создаем кнопку авторизации
                keyboard = [
                    [InlineKeyboardButton("🔑 Авторизоваться", callback_data="authorize")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    "❌ **Доступ к системе отсутствует**\n\n"
                    "**Возможные причины:**\n"
                    "• Вы не зарегистрированы в системе\n"
                    "• Ваш аккаунт был удален администратором\n"
                    "• Ваш аккаунт деактивирован\n\n"
                    f"**Ваши данные для администратора:**\n"
                    f"• Telegram ID: `{user.id}`\n"
                    f"• Username: @{user.username or 'не указан'}\n"
                    f"• Имя: {user.first_name} {user.last_name or ''}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return

            context.user_data['db_user'] = db_user
            return await func(update, context)
        return wrapper

    async def try_auto_authorize(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Попытка автоматической авторизации"""
        try:
            import requests
            response = requests.post(f'{API_BASE_URL}/telegram/auto-auth', json={
                'telegram_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name
            }, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return data.get('success', False), data.get('message', ''), data.get('user')
            else:
                return False, "Ошибка сервера", None
        except Exception as e:
            logger.error(f"Ошибка автоматической авторизации: {e}")
            return False, "Ошибка подключения к серверу", None

    # Методы для создания задач
    def init_task_creation(self, user_id: int):
        """Инициализация создания задачи"""
        return {
            'user_id': user_id,
            'step': 'role_selection',  # role_selection -> user_selection -> project_selection -> task_type -> format (для дизайнеров) -> deadline -> confirmation
            'role': None,
            'executor_id': None,
            'project': None,
            'task_type': None,
            'task_format': None,
            'title': None,
            'description': None,
            'deadline': None,
            'deadline_date': None,
            'deadline_time': None
        }

    def get_users_by_role(self, role: str):
        """Получение пользователей по роли"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE role = ? AND is_active = 1",
                (role,)
            )
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Ошибка получения пользователей по роли: {e}")
            conn.close()
            return []

    def get_all_projects(self):
        """Получение всех активных проектов"""
        conn = self.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE is_archived = 0 ORDER BY name"
            )
            projects = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return projects
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
            conn.close()
            return []

    async def get_task_types_from_api(self, role: str = None):
        """Получение типов задач из API"""
        try:
            import aiohttp
            url = f'{API_BASE_URL}/tasks/types'
            if role:
                url += f'?role={role}'

            timeout = aiohttp.ClientTimeout(total=5)  # Уменьшил таймаут до 5 секунд
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if role:
                            # Возвращаем список типов для конкретной роли
                            return [(f"{item['icon']} {item['name']}", item['name']) for item in data]
                        else:
                            # Возвращаем все типы
                            return data
                    else:
                        # Fallback к старым значениям при ошибке API
                        return self.get_fallback_task_types(role)
        except Exception as e:
            logger.error(f"Ошибка получения типов задач из API: {e}")
            return self.get_fallback_task_types(role)

    async def get_task_formats_from_api(self):
        """Получение форматов задач из API"""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f'{API_BASE_URL}/tasks/formats') as response:
                    if response.status == 200:
                        data = await response.json()
                        return [(f"{item['icon']} {item['name']}", item['name']) for item in data]
                    else:
                        # Fallback к старым значениям при ошибке API
                        return self.get_fallback_task_formats()
        except Exception as e:
            logger.error(f"Ошибка получения форматов задач из API: {e}")
            return self.get_fallback_task_formats()

    def get_fallback_task_types(self, role: str = None):
        """Fallback типы задач если API недоступен"""
        task_types_map = {
            'designer': [
                ("🎞️ Motion", "Motion"),
                ("🖼️ Статика", "Статика"),
                ("🎬 Видео", "Видео"),
                ("🖼️ Карусель", "Карусель"),
                ("📌 Другое", "Другое")
            ],
            'smm_manager': [
                ("📝 Публикация", "Публикация"),
                ("📅 Контент план", "Контент план"),
                ("📊 Отчет", "Отчет"),
                ("📹 Съемка", "Съемка"),
                ("🤝 Встреча", "Встреча"),
                ("📈 Стратегия", "Стратегия"),
                ("🎤 Презентация", "Презентация"),
                ("🗂️ Админ задачи", "Админ задачи"),
                ("🔎 Анализ", "Анализ"),
                ("📋 Брифинг", "Брифинг"),
                ("📜 Сценарий", "Сценарий"),
                ("📌 Другое", "Другое")
            ],
            'digital': [
                ("🎯 Настройка рекламы", "Настройка рекламы"),
                ("📈 Анализ эффективности", "Анализ эффективности"),
                ("🧪 A/B тестирование", "A/B тестирование"),
                ("📊 Настройка аналитики", "Настройка аналитики"),
                ("💰 Оптимизация конверсий", "Оптимизация конверсий"),
                ("📧 Email-маркетинг", "Email-маркетинг"),
                ("🔍 Контекстная реклама", "Контекстная реклама"),
                ("🎯 Таргетированная реклама", "Таргетированная реклама"),
                ("🔍 SEO оптимизация", "SEO оптимизация"),
                ("📊 Веб-аналитика", "Веб-аналитика"),
                ("📌 Другое", "Другое")
            ]
        }

        if role:
            return task_types_map.get(role, [])

        # Старые значения для совместимости
        return [
            ("🎨 Креативная", "creative"),
            ("📝 Контент", "content"),
            ("🔧 Техническая", "technical"),
            ("📊 Аналитическая", "analytics"),
            ("📞 Общение", "communication"),
            ("🎬 Видео", "video")
        ]

    def get_fallback_task_formats(self):
        """Fallback форматы задач если API недоступен"""
        return [
            ("📱 9:16", "9:16"),
            ("🔲 1:1", "1:1"),
            ("🖼️ 4:5", "4:5"),
            ("🎞️ 16:9", "16:9"),
            ("📌 Другое", "Другое")
        ]

    def create_keyboard_3_per_row(self, buttons_data, back_button=None):
        """Создание клавиатуры с кнопками по 3 в ряд"""
        keyboard = []
        row = []

        for button_text, callback_data in buttons_data:
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем оставшиеся кнопки, если есть
        if row:
            keyboard.append(row)

        # Добавляем кнопку "Назад" в отдельный ряд, если указана
        if back_button:
            keyboard.append([InlineKeyboardButton(back_button[0], callback_data=back_button[1])])

        return keyboard

    async def clear_chat_history(self, update: Update, context, limit: int = 50):
        """Очистка истории чата (удаление последних N сообщений)"""
        try:
            chat_id = update.effective_chat.id
            message_id = update.effective_message.message_id

            # Удаляем последние N сообщений
            for i in range(1, limit + 1):
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id - i)
                except Exception:
                    # Сообщение не найдено или уже удалено
                    pass
        except Exception as e:
            logger.error(f"Ошибка очистки истории чата: {e}")

    async def start_command(self, update: Update, context):
        """Команда /start"""
        user = update.effective_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)

        # Если пользователь не найден, пытаемся автоматическую авторизацию
        if not db_user:
            success, message, api_user = await self.try_auto_authorize(
                user.id,
                user.username,
                user.first_name,
                user.last_name
            )

            if success:
                # Перезапрашиваем пользователя из базы
                db_user = self.get_user_by_telegram_id(user.id, user.username)

        if db_user:
            # Определяем эмоджи для роли
            role_emojis = {
                'designer': '🎨',
                'smm_manager': '📱',
                'digital': '💻',
                'admin': '🔑',
                'head_smm': '👑'
            }

            role_names = {
                'designer': 'Дизайнер',
                'smm_manager': 'СММ-менеджер',
                'digital': 'Digital',
                'admin': 'Администратор',
                'head_smm': 'Руководитель СММ'
            }

            role_emoji = role_emojis.get(db_user['role'], '👤')
            role_name = role_names.get(db_user['role'], db_user['role'])

            # Создаем кнопки для основных действий
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы"],
                ["🗑️ Очистить историю сообщений"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            # Определяем статус активации
            access_status = "🟢 Активирован" if db_user['role'] != 'inactive' else "🔴 Не активирован"

            message = f"""Добро пожаловать в 8Bit Digital!


👤 {db_user['name']} — наш 🏆 {role_name}

🔑 Уровень доступа: {access_status}


Готовы взять новый проект в работу?

Выберите действие ниже ⬇️"""

            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            return
        else:
            # Создаем кнопку авторизации
            keyboard = [
                [InlineKeyboardButton("🔑 Авторизоваться", callback_data="authorize")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = f"""
🎯 **Система управления задачами 8Bit**

❌ **Доступ к системе отсутствует**

**Возможные причины:**
• Вы не зарегистрированы в системе
• Ваш аккаунт был удален администратором
• Ваш аккаунт деактивирован

**Ваши данные для администратора:**
• Telegram ID: `{user.id}`
• Username: @{user.username or 'не указан'}
• Имя: {user.first_name} {user.last_name or ''}
            """

            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            return

    async def help_command(self, update: Update, context):
        """Команда /help"""
        help_text = """
🤖 **Справка по боту системы 8Bit**

**📋 Основные команды:**
/start - Начать работу с ботом
/tasks - Посмотреть мои задачи
/projects - Посмотреть мои проекты
/expenses - Посмотреть мои расходы
/status - Статус системы
/help - Эта справка

**🔐 Авторизация:**
Для работы с системой администратор должен добавить вас:
1. Отправьте /start и скопируйте ваши данные
2. Передайте их администратору
3. После добавления все команды будут доступны

**🚀 Возможности:**
• Просмотр задач и их статусов
• Информация о проектах
• Учет личных расходов
• Получение уведомлений

**📞 Поддержка:**
Обратитесь к администратору системы.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context):
        """Команда /status - статус системы"""
        try:
            import requests
            response = requests.get(f'{API_BASE_URL}/health', timeout=5)
            backend_status = "✅ Работает" if response.status_code == 200 else "❌ Ошибка"
        except:
            backend_status = "❌ Недоступен"

        # Проверка базы данных
        conn = self.get_db_connection()
        db_status = "✅ Доступна" if conn else "❌ Недоступна"
        if conn:
            conn.close()

        user = update.effective_user
        message = f"""
📊 **Статус системы 8Bit**

🔧 **Компоненты:**
• Backend API: {backend_status}
• База данных: {db_status}
• Telegram Bot: ✅ Работает

👤 **Ваши данные:**
• ID: `{user.id}`
• Username: @{user.username or 'не указан'}

🌐 **Ссылки:**
• API: {API_BASE_URL}
• База данных: {DATABASE_PATH}

⏰ Время проверки: {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    @property
    def tasks_command(self):
        return self.require_auth(self._tasks_command)

    async def _tasks_command(self, update: Update, context):
        """Команда /tasks - мои задачи"""
        db_user = context.user_data['db_user']
        tasks = self.get_user_tasks(db_user['id'])

        if not tasks:
            await update.message.reply_text(
                "📋 **Мои задачи**\n\n"
                "У вас пока нет задач.",
                parse_mode='Markdown'
            )
            return

        message = "📋 **Мои задачи**\n\n"
        for task in tasks:
            status_emoji = {
                'new': '⏳',
                'in_progress': '🔄',
                'done': '✅',
                'cancelled': '❌'
            }.get(task['status'], '❓')

            message += f"{status_emoji} **{task['title']}**\n"
            message += f"   Проект: {task['project_name'] or 'Не указан'}\n"
            message += f"   Статус: {task['status']}\n"
            if task['deadline']:
                message += f"   Дедлайн: {task['deadline']}\n"
            message += "\n"

        # Кнопки для действий
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tasks")],
            [InlineKeyboardButton("📊 Статистика", callback_data="task_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @property
    def projects_command(self):
        return self.require_auth(self._projects_command)

    async def _projects_command(self, update: Update, context):
        """Команда /projects - мои проекты"""
        db_user = context.user_data['db_user']
        projects = self.get_user_projects(db_user['id'])

        if not projects:
            await update.message.reply_text(
                "📁 **Мои проекты**\n\n"
                "У вас пока нет проектов.",
                parse_mode='Markdown'
            )
            return

        message = "📁 **Мои проекты**\n\n"
        for project in projects:
            status_emoji = {
                'active': '🟢',
                'completed': '✅',
                'paused': '⏸️',
                'cancelled': '❌'
            }.get(project['status'], '❓')

            message += f"{status_emoji} **{project['name']}**\n"
            if project['description']:
                message += f"   {project['description'][:100]}...\n" if len(project['description']) > 100 else f"   {project['description']}\n"
            message += f"   Статус: {project['status']}\n"
            message += "\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_projects")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @property
    def expenses_command(self):
        return self.require_auth(self._expenses_command)

    async def _expenses_command(self, update: Update, context):
        """Команда /expenses - мои расходы"""
        db_user = context.user_data['db_user']
        expenses = self.get_user_expenses(db_user['id'])

        if not expenses:
            await update.message.reply_text(
                "💰 **Мои расходы**\n\n"
                "У вас пока нет записей о расходах.",
                parse_mode='Markdown'
            )
            return

        message = "💰 **Мои расходы**\n\n"
        total = 0

        for expense in expenses:
            amount = float(expense['amount']) if expense['amount'] else 0
            total += amount

            message += f"💳 **{expense['description']}**\n"
            message += f"   Сумма: {amount:.2f} ₽\n"
            message += f"   Дата: {expense['date']}\n"
            if expense['project_name']:
                message += f"   Проект: {expense['project_name']}\n"
            message += "\n"

        message += f"**Общая сумма: {total:.2f} ₽**"

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_expenses")],
            [InlineKeyboardButton("📊 Статистика", callback_data="expense_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_user_task_management(self, update, context):
        """Меню управления задачами для обычного пользователя"""
        keyboard = [
            ["📋 Принятые в работу", "📝 Мои задачи"],
            ["🔧 Управление задачами"],
            ["💰 Расходы"],
                    ["🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "🔧 **Управление задачами** 🔧\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def show_user_in_progress_tasks(self, update, context):
        """Показать задачи пользователя принятые в работу"""
        user = update.effective_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)

        if not db_user:
            await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
            return

        tasks = self.get_user_in_progress_tasks(db_user['id'])

        if not tasks:
            await update.message.reply_text(
                "📋 **Принятые в работу**\n\n"
                "У вас нет задач принятых в работу.",
                parse_mode='Markdown'
            )
            return

        message = "📋 **Принятые в работу**\n\n"
        for task in tasks:
            status_emoji = '🔄'  # in_progress
            priority_emoji = '🔥' if task.get('high_priority') else ''

            message += f"{status_emoji} **{task['title']}**{priority_emoji}\n"
            if task.get('description'):
                # Ограничиваем описание 100 символами
                desc = task['description'][:100] + "..." if len(task['description']) > 100 else task['description']
                message += f"   📝 {desc}\n"
            if task.get('project'):
                message += f"   📁 Проект: {task['project']}\n"
            if task.get('deadline'):
                deadline = task['deadline']
                message += f"   ⏰ Дедлайн: {deadline}\n"
            message += "\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_in_progress_tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_callback_query(self, update: Update, context):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()

        if query.data == "authorize":
            await self.handle_authorize_button(query, context)
        # Главное меню
        elif query.data == "admin_task_management":
            await self.admin_handlers.handle_admin_task_management(query, context)
        elif query.data == "my_tasks":
            await self._tasks_command(query, context)
        elif query.data == "create_task":
            await self.handle_create_task_start_from_callback(query, context)
        elif query.data == "my_projects":
            await self._projects_command(query, context)
        elif query.data == "my_expenses":
            await self.expense_handlers.handle_expenses_menu(query, context)
        elif query.data == "add_expense":
            await self.expense_handlers.handle_add_expense_start(query, context)
        elif query.data == "view_expenses":
            await self.expense_handlers.handle_view_expenses_periods(query, context)
        elif query.data.startswith("period_"):
            await self.expense_handlers.handle_period_selection(query, context)
        elif query.data.startswith("project_"):
            await self.expense_handlers.handle_project_selection(query, context)
        elif query.data == "skip_description":
            await self.expense_handlers.handle_skip_description(query, context)
        elif query.data == "user_task_management":
            await self.admin_handlers.handle_admin_task_management(query, context)
        # Обработчики кнопок задач
        elif query.data.startswith("complete_task_"):
            task_id = query.data.replace("complete_task_", "")
            await self.handle_complete_task(query, context, task_id)
        elif query.data.startswith("delete_task_"):
            task_id = query.data.replace("delete_task_", "")
            await self.handle_delete_task(query, context, task_id)
        elif query.data == "reports":
            await self.handle_reports_menu(query, context)
        # Старые обработчики создания задач убраны - теперь всё через ReplyKeyboard
        # Старые обработчики
        elif query.data == "refresh_tasks":
            await self._tasks_command(query, context)
        elif query.data == "refresh_in_progress_tasks":
            await self.show_user_in_progress_tasks(query, context)
        elif query.data == "refresh_projects":
            await self._projects_command(query, context)
        elif query.data == "refresh_expenses":
            await self._expenses_command(query, context)
        elif query.data == "task_stats":
            await self._task_statistics(query, context)
        elif query.data == "expense_stats":
            await self._expense_statistics(query, context)
        # Новые обработчики администратора
        elif query.data == "admin_create_task":
            await self.admin_handlers.handle_admin_create_task(query, context)
        elif query.data.startswith("select_role_"):
            await self.admin_handlers.handle_role_selection(query, context)
        elif query.data.startswith("executor_page_"):
            await self.admin_handlers.handle_executor_page(query, context)
        elif query.data.startswith("select_executor_"):
            await self.admin_handlers.handle_executor_selection(query, context)
        elif query.data.startswith("project_page_"):
            await self.admin_handlers.handle_project_page(query, context)
        elif query.data.startswith("select_project_") and 'admin_task_creation' in context.user_data:
            await self.admin_handlers.handle_project_selection(query, context)
        elif query.data.startswith("select_task_type_") and 'admin_task_creation' in context.user_data:
            await self.admin_handlers.handle_task_type_selection(query, context)
        elif query.data.startswith("select_format_"):
            await self.admin_handlers.handle_format_selection(query, context)
        elif query.data == "back_to_main":
            await self.handle_back_to_main(query, context)
        elif query.data.startswith("accept_task_"):
            task_id = query.data.replace("accept_task_", "")
            await self.handle_accept_task_callback(query, context, task_id)
        else:
            logger.warning(f"Неизвестный callback: {query.data}")

    async def handle_reports_menu(self, query, context):
        """Обработчик меню отчетов (заглушка)"""
        try:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = """
📊 **Отчеты**

🚧 **Раздел находится в разработке**

Здесь будут доступны различные отчеты по:
• Расходам сотрудников
• Выполненным задачам
• Статистике проектов
• Аналитике по периодам

⚠️ *Функционал будет добавлен в ближайшее время*
            """

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в handle_reports_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_accept_task_callback(self, query, context, task_id):
        """Обработка принятия задачи в работу через callback кнопку"""
        try:
            # Меняем статус задачи напрямую в БД
            conn = self.get_db_connection()
            if not conn:
                await query.edit_message_text(
                    "❌ Ошибка подключения к базе данных",
                    parse_mode='Markdown'
                )
                return

            # Обновляем статус задачи
            from datetime import datetime
            accepted_at = datetime.now().isoformat()

            cursor = self._execute_query(conn,
                "UPDATE tasks SET status = 'in_progress', accepted_at = ? WHERE id = ?",
                (accepted_at, task_id)
            )
            conn.commit()

            if cursor.rowcount > 0:
                conn.close()
                await query.edit_message_text(
                    f"✅ **Задача #{task_id} принята в работу!**\n\n"
                    f"Статус изменен на 'В работе'",
                    parse_mode='Markdown'
                )
            else:
                conn.close()
                await query.edit_message_text(
                    f"❌ Задача #{task_id} не найдена",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка при принятии задачи #{task_id}: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при принятии задачи",
                parse_mode='Markdown'
            )

    async def handle_back_to_main(self, query, context):
        """Возврат в главное меню"""
        user = query.from_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)

        if db_user:
            # Очищаем данные создания задачи
            context.user_data.pop('admin_task_creation', None)

            # Определяем эмоджи для роли
            role_emojis = {
                'designer': '🎨',
                'smm_manager': '📱',
                'digital': '💻',
                'admin': '🔑',
                'head_smm': '👑'
            }

            role_names = {
                'designer': 'Дизайнер',
                'smm_manager': 'СММ-менеджер',
                'digital': 'Digital',
                'admin': 'Администратор',
                'head_smm': 'Руководитель СММ'
            }

            role_emoji = role_emojis.get(db_user['role'], '👤')
            role_name = role_names.get(db_user['role'], db_user['role'])

            # Создаем кнопки для основных действий
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы"],
                ["🗑️ Очистить историю сообщений"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            # Определяем статус активации
            access_status = "🟢 Активирован" if db_user['role'] != 'inactive' else "🔴 Не активирован"

            message = f"""Добро пожаловать в 8Bit Digital!


👤 {db_user['name']} — наш 🏆 {role_name}

🔑 Уровень доступа: {access_status}


Готовы взять новый проект в работу?

Выберите действие ниже ⬇️"""

            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_authorize_button(self, query, context):
        """Обработчик кнопки авторизации"""
        user = query.from_user

        # Показываем индикатор загрузки
        await query.edit_message_text("🔄 **Попытка авторизации...**\n\nПроверяем ваши данные в системе...", parse_mode='Markdown')

        # Пытаемся авторизоваться
        success, message, api_user = await self.try_auto_authorize(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )

        if success:
            # Проверяем, что пользователь действительно добавился
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if db_user:
                await query.edit_message_text(
                    f"✅ **Авторизация успешна!**\n\n"
                    f"👤 **Добро пожаловать, {db_user['name']}!**\n"
                    f"🔹 Роль: {db_user['role']}",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"✅ **{message}**\n\n"
                    f"Попробуйте выполнить команду /start еще раз.",
                    parse_mode='Markdown'
                )
        else:
            # Создаем кнопку для повторной попытки
            keyboard = [
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="authorize")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"❌ **Авторизация не удалась**\n\n"
                f"**Возможные причины:**\n"
                f"• Вы не зарегистрированы в системе\n"
                f"• Ваш аккаунт был удален администратором\n"
                f"• Ваш аккаунт деактивирован\n"
                f"• Технические проблемы: {message}\n\n"
                f"**Ваши данные для администратора:**\n"
                f"• Telegram ID: `{user.id}`\n"
                f"• Username: @{user.username or 'не указан'}\n"
                f"• Имя: {user.first_name} {user.last_name or ''}\n\n"
                f"📞 **Обратитесь к администратору для получения/восстановления доступа**",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    # Обработчики создания задач
    async def handle_create_task_start_from_callback(self, query, context):
        """Начало создания задачи из callback (inline кнопки)"""
        user = query.from_user

        # Инициализируем создание задачи
        context.user_data['task_creation'] = self.init_task_creation(user.id)

        # Создаем ReplyKeyboard с ролями
        role_buttons = ["🎨 Дизайнер", "📱 СММ-менеджер", ]
        reply_markup = self.create_reply_keyboard_3_per_row(role_buttons, "🔙 Отмена")

        # Убираем inline клавиатуру из старого сообщения
        await query.edit_message_text(
            "📋 **Главное меню**",
            parse_mode='Markdown'
        )

        # Отправляем новое сообщение с ReplyKeyboard
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="➕ **Создание новой задачи**\n\n"
                 "👥 **Выберите роль исполнителя:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_create_task_start(self, update, context):
        """Начало создания задачи через команду"""
        user = update.effective_user

        # Инициализируем создание задачи
        context.user_data['task_creation'] = self.init_task_creation(user.id)

        # Создаем ReplyKeyboard с ролями
        role_buttons = ["🎨 Дизайнер", "📱 СММ-менеджер", ]
        reply_markup = self.create_reply_keyboard_3_per_row(role_buttons, "🔙 Отмена")

        # Отправляем сообщение с ReplyKeyboard
        await update.message.reply_text(
            "➕ **Создание новой задачи**\n\n"
            "👥 **Выберите роль исполнителя:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_user_selection_with_reply(self, update, context):
        """Обработка выбора пользователя с ReplyKeyboard"""
        task_data = context.user_data.get('task_creation', {})
        role = task_data.get('role', '')

        # Получаем пользователей с выбранной ролью
        users = self.get_users_by_role(role)

        if not users:
            await update.message.reply_text(
                f"❌ **Нет активных пользователей с ролью {role}**\n\n"
                "🔙 **Возвращайтесь к выбору роли**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Сохраняем пользователей в контексте для последующего использования
        task_data['available_users'] = users
        context.user_data['task_creation'] = task_data

        # Создаем кнопки с пользователями
        user_buttons = [f"👤 {user['name']}" for user in users]
        reply_markup = self.create_reply_keyboard_3_per_row(user_buttons, "🔙 Назад")

        role_names = {
            'designer': 'Дизайнер',
            'smm_manager': 'СММ-менеджер',
            'digital': 'Digital'
        }

        await update.message.reply_text(
            f"➕ **Создание новой задачи**\n\n"
            f"🏆 **Роль:** {role_names.get(role, role)}\n\n"
            "👤 **Выберите исполнителя:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_project_selection_with_reply(self, update, context):
        """Обработка выбора проекта с ReplyKeyboard"""
        task_data = context.user_data.get('task_creation', {})

        # Получаем проекты
        projects = self.get_all_projects()

        if not projects:
            await update.message.reply_text(
                "❌ **Нет доступных проектов**\n\n"
                "🔙 **Возвращайтесь к выбору пользователя**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Сохраняем проекты в контексте
        task_data['available_projects'] = projects
        context.user_data['task_creation'] = task_data

        # Создаем кнопки с проектами
        project_buttons = [f"📁 {project['name']}" for project in projects]
        reply_markup = self.create_reply_keyboard_3_per_row(project_buttons, "🔙 Назад")

        await update.message.reply_text(
            "➕ **Создание новой задачи**\n\n"
            "📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_user_selection(self, query, context):
        """Обработка выбора пользователя"""
        executor_id = int(query.data.replace("select_user_", ""))

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['executor_id'] = executor_id
        task_data['step'] = 'project_selection'
        context.user_data['task_creation'] = task_data

        # Получаем проекты
        projects = self.get_all_projects()

        if not projects:
            await query.edit_message_text(
                "❌ **Нет доступных проектов**\n\n"
                "🔙 **Возвращайтесь к выбору пользователя**",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data=f"select_role_{task_data.get('role', '')}")
                ]])
            )
            return

        # Создаем кнопки с проектами (по 2 в ряд)
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for j in range(2):
                if i + j < len(projects):
                    project = projects[i + j]
                    row.append(InlineKeyboardButton(
                        f"📁 {project['name']}",
                        callback_data=f"select_project_{project['id']}"
                    ))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_role_{task_data.get('role', '')}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "➕ **Создание новой задачи**\n\n"
            "📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _task_statistics(self, update, context):
        """Статистика по задачам"""
        db_user = context.user_data['db_user']
        conn = self.get_db_connection()

        query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None

        if not conn:
            if query:
                await query.edit_message_text("❌ Ошибка подключения к базе данных")
            else:
                await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return

        try:
            cursor = self._execute_query(conn, """
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE assigned_to = ?
                GROUP BY status
            """, (db_user['id'],))

            stats = dict(cursor.fetchall())
            conn.close()

            message = "📊 **Статистика задач**\n\n"
            for status, count in stats.items():
                emoji = {
                    'new': '⏳',
                    'in_progress': '🔄',
                    'done': '✅',
                    'cancelled': '❌'
                }.get(status, '❓')
                message += f"{emoji} {status}: {count}\n"

            if query:
                await query.edit_message_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка статистики задач: {e}")
            if query:
                await query.edit_message_text("❌ Ошибка получения статистики")
            else:
                await update.message.reply_text("❌ Ошибка получения статистики")

    async def _expense_statistics(self, update, context):
        """Статистика по расходам"""
        db_user = context.user_data['db_user']
        conn = self.get_db_connection()

        query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None

        if not conn:
            if query:
                await query.edit_message_text("❌ Ошибка подключения к базе данных")
            else:
                await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return

        try:
            cursor = self._execute_query(conn, """
                SELECT
                    COUNT(*) as total_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM employee_expenses
                WHERE employee_id = ?
            """, (db_user['id'],))

            stats = cursor.fetchone()
            conn.close()

            message = "📊 **Статистика расходов**\n\n"
            message += f"📝 Всего записей: {stats['total_count']}\n"
            message += f"💰 Общая сумма: {stats['total_amount']:.2f} ₽\n"
            message += f"📈 Средняя сумма: {stats['avg_amount']:.2f} ₽\n"

            if query:
                await query.edit_message_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка статистики расходов: {e}")
            if query:
                await query.edit_message_text("❌ Ошибка получения статистики")
            else:
                await update.message.reply_text("❌ Ошибка получения статистики")

    async def unknown_command(self, update: Update, context):
        """Обработчик неизвестных команд"""
        message = """
❓ **Неизвестная команда**

**Доступные команды:**
/start - Начать работу
/tasks - Мои задачи
/projects - Мои проекты
/expenses - Мои расходы
/status - Статус системы
/help - Справка

Введите /help для получения подробной информации.
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def text_message(self, update: Update, context):
        """Обработчик текстовых сообщений"""
        # Игнорируем сообщения от ботов (включая самого себя)
        if update.message.from_user.is_bot:
            return

        text = update.message.text.strip()
        user = update.effective_user

        # Обработка кнопки возврата в главное меню (должна быть первой)
        if text == "🔙 Главное меню" or text == "🔙 Назад" or text == "🏠 Главное меню":
            # Возвращаемся к главному меню без очистки истории
            await self.start_command(update, context)
            return

        # Обработка кнопки очистки истории
        if text == "🗑️ Очистить историю сообщений":
            await self.clear_chat_history(update, context, limit=100)
            await update.message.reply_text("✅ История сообщений очищена")
            # Показываем главное меню
            await self.start_command(update, context)
            return

        # Обработка кнопок главного меню
        if text == "🔧 Управление задачами":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            if db_user['role'] == 'admin':
                await self.admin_handlers.handle_admin_task_management(update, context)
            else:
                await self.user_task_handlers.handle_user_task_management(update, context)
            return

        elif text == "💰 Расходы":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            await self.expense_handlers.handle_expenses_menu(update, context)
            return

        elif text == "➕ Добавить расход":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            await self.expense_handlers.handle_add_expense_start(update, context)
            return

        elif text == "📋 Просмотреть мои расходы":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            await self.expense_handlers.handle_view_expenses_start(update, context)
            return

        elif text in ["📅 Январь", "📅 Февраль", "📅 Март", "📅 Апрель", "📅 Май", "📅 Июнь",
                      "📅 Июль", "📅 Август", "📅 Сентябрь", "📅 Октябрь", "📅 Ноябрь", "📅 Декабрь",
                      "📅 За все время", "📅 За сегодня", "📅 За неделю", "📅 За месяц"]:
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            # Проверяем контекст - если это архивные задачи, передаем в admin_handlers
            archived_data = context.user_data.get('archived_tasks_view')
            if archived_data and archived_data.get('step') == 'period_selection':
                # Обработка в admin_handlers
                if db_user['role'] == 'admin':
                    await self.admin_handlers.handle_archived_tasks_period_selection(update, context, text)
                    return

            # Иначе это расходы
            await self.expense_handlers.handle_period_selection_text(update, context, text)
            return

        elif text == "📋 Принятые в работу":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            await self.show_user_in_progress_tasks(update, context)
            return

        elif text == "📝 Мои задачи":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if not db_user:
                await update.message.reply_text("❌ Необходима авторизация. Используйте /start")
                return

            await self._tasks_command(update, context)
            return

        # Обработка администраторских задач
        admin_task_data = context.user_data.get('admin_task_creation')
        if admin_task_data and text == "❌ Отмена":
            # Очищаем данные создания задачи и возвращаемся в главное меню
            context.user_data.pop('admin_task_creation', None)
            await self.start_command(update, context)
            return

        # Обработка редактирования - выбор шага для изменения
        if admin_task_data and admin_task_data.get('step') == 'edit_selection':
            if text.startswith("👤 Роль:"):
                # Возвращаемся к выбору роли
                admin_task_data['step'] = 'role_selection'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_admin_create_task(update, context)
                return
            elif text.startswith("👷 Исполнитель:"):
                # Возвращаемся к выбору исполнителя
                admin_task_data['step'] = 'executor_selection'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data
                role = admin_task_data.get('executor_role')
                await self.admin_handlers._process_role_selection(update, context, role, is_callback=False)
                return
            elif text.startswith("📁 Проект:"):
                # Возвращаемся к выбору проекта
                admin_task_data['step'] = 'project_selection'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data

                projects = await self.admin_handlers.get_all_projects()
                keyboard = []
                for project in projects:
                    keyboard.append([f"📁 {project['name']}"])
                keyboard.append(["🔙 Назад"])
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    f"➕ **Создание новой задачи**\n\n"
                    f"📁 **Выберите проект:**",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            elif text.startswith("🏷️ Тип задачи:"):
                # Возвращаемся к выбору типа задачи
                admin_task_data['step'] = 'task_type_selection'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data

                executor_role = admin_task_data.get('executor_role')
                task_types = await self.admin_handlers.get_task_types_by_role(executor_role)

                keyboard = []
                for task_type in task_types:
                    keyboard.append([task_type])
                keyboard.append(["🔙 Назад"])
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    f"➕ **Создание новой задачи**\n\n"
                    f"🏷️ **Выберите тип задачи:**",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            elif text.startswith("📐 Формат:"):
                # Возвращаемся к выбору формата
                admin_task_data['step'] = 'format_selection'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.show_format_selection(update, context)
                return
            elif text.startswith("📝 Название:"):
                # Возвращаемся к вводу названия
                admin_task_data['step'] = 'title_input'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data

                keyboard = ReplyKeyboardMarkup(
                    [["❌ Отмена"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )

                await update.message.reply_text(
                    "➕ **Создание новой задачи**\n\n"
                    "📝 **Название задачи:**\n\n"
                    "Напишите краткое и понятное название в следующем сообщении.",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                return
            elif text.startswith("📋 Описание:"):
                # Возвращаемся к вводу описания
                admin_task_data['step'] = 'description_prompt'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_description_prompt(update, context)
                return
            elif text.startswith("⏰ Дедлайн:"):
                # Возвращаемся к установке дедлайна
                admin_task_data['step'] = 'deadline_input'
                admin_task_data['return_to_preview'] = True
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_deadline_prompt(update, context)
                return
            elif text == "🔙 Вернуться к просмотру":
                # Возвращаемся к предпросмотру
                admin_task_data['step'] = 'final_confirmation'
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.show_task_preview(update, context)
                return

        # Обработка кнопки "Назад" в просмотре активных задач
        active_tasks_data = context.user_data.get('active_tasks_view')
        if active_tasks_data and text == "🔙 Назад":
            # Очищаем данные просмотра активных задач и возвращаемся к админ меню
            context.user_data.pop('active_tasks_view', None)
            await self.admin_handlers.handle_admin_task_management(update, context)
            return

        # Обработка кнопки "Назад" в создании админской задачи
        if admin_task_data and text == "🔙 Назад":
            current_step = admin_task_data.get('step')

            if current_step == 'role_selection':
                # Возвращаемся к меню управления задачами
                await self.admin_handlers.handle_admin_task_management(update, context)
                return
            elif current_step == 'executor_selection':
                # Возвращаемся к выбору роли
                admin_task_data['step'] = 'role_selection'
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_admin_create_task(update, context)
                return
            elif current_step == 'project_selection':
                # Возвращаемся к выбору исполнителя
                admin_task_data['step'] = 'role_selection'
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_admin_create_task(update, context)
                return
            elif current_step == 'task_type_selection':
                # Возвращаемся к выбору проекта
                admin_task_data['step'] = 'project_selection'
                context.user_data['admin_task_creation'] = admin_task_data
                executor_name = admin_task_data.get('executor_name', '')
                await self.admin_handlers.handle_executor_selection(update, context, executor_name)
                return
            elif current_step == 'format_selection':
                # Возвращаемся к выбору типа задачи
                admin_task_data['step'] = 'task_type_selection'
                context.user_data['admin_task_creation'] = admin_task_data
                project_name = admin_task_data.get('project_name', '')
                await self.admin_handlers.handle_project_selection(update, context, project_name)
                return
            elif current_step == 'title_input':
                # Возвращаемся к предыдущему шагу в зависимости от роли
                if admin_task_data.get('executor_role') == 'designer' and admin_task_data.get('format'):
                    # Для дизайнера возвращаемся к выбору формата
                    admin_task_data['step'] = 'format_selection'
                    context.user_data['admin_task_creation'] = admin_task_data
                    task_type_text = self.admin_handlers.get_task_type_name(admin_task_data.get('task_type', ''))
                    await self.admin_handlers.handle_task_type_selection(update, context, task_type_text)
                else:
                    # Для других ролей возвращаемся к выбору типа задачи
                    admin_task_data['step'] = 'task_type_selection'
                    context.user_data['admin_task_creation'] = admin_task_data
                    project_name = admin_task_data.get('project_name', '')
                    await self.admin_handlers.handle_project_selection(update, context, project_name)
                return
            elif current_step == 'description_input':
                # Возвращаемся к вводу названия
                admin_task_data['step'] = 'title_input'
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.start_title_input(update, context)
                return
            elif current_step == 'description_text_input':
                # Возвращаемся к выбору добавления описания
                admin_task_data['step'] = 'description_input'
                context.user_data['admin_task_creation'] = admin_task_data
                title = admin_task_data.get('title', '')
                await self.admin_handlers.handle_title_input(update, context, title)
                return
            elif current_step == 'deadline_input':
                # Возвращаемся к описанию (если есть) или к названию
                if admin_task_data.get('description'):
                    admin_task_data['step'] = 'description_text_input'
                    context.user_data['admin_task_creation'] = admin_task_data
                    await self.admin_handlers.handle_description_prompt(update, context)
                else:
                    admin_task_data['step'] = 'description_input'
                    context.user_data['admin_task_creation'] = admin_task_data
                    title = admin_task_data.get('title', '')
                    await self.admin_handlers.handle_title_input(update, context, title)
                return
            elif current_step == 'final_confirmation':
                # Возвращаемся к установке дедлайна
                admin_task_data['step'] = 'deadline_input'
                context.user_data['admin_task_creation'] = admin_task_data
                await self.admin_handlers.handle_deadline_prompt(update, context)
                return

        # Обработка выбора роли в создании админской задачи
        if admin_task_data and admin_task_data.get('step') == 'role_selection':
            # Проверяем, является ли это выбором роли
            role_buttons = ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер", ]
            if text in role_buttons:
                await self.admin_handlers.handle_role_selection_text(update, context)
                return

        # Обработка выбора исполнителя в создании админской задачи
        if admin_task_data and admin_task_data.get('step') == 'executor_selection':
            # Проверяем, является ли это выбором исполнителя
            if text.startswith("👤 ") and text != "👤":
                await self.admin_handlers.handle_executor_selection_text(update, context)
                return

        # Обработка выбора проекта в создании админской задачи
        if admin_task_data and admin_task_data.get('step') == 'project_selection':
            # Проверяем, является ли это выбором проекта
            if text.startswith("📁 ") and text != "📁":
                await self.admin_handlers.handle_project_selection_text(update, context)
                return

        # Обработка выбора типа задачи в создании админской задачи
        if admin_task_data and admin_task_data.get('step') == 'task_type_selection':
            # Получаем доступные типы задач динамически из API
            executor_role = admin_task_data.get('executor_role')
            available_task_types = await self.admin_handlers.get_task_types_by_role(executor_role)
            if text in available_task_types:
                await self.admin_handlers.handle_task_type_selection_text(update, context)
                return

        # Обработка выбора формата в создании админской задачи (для дизайнеров)
        if admin_task_data and admin_task_data.get('step') == 'format_selection':
            # Получаем доступные форматы динамически из API
            try:
                formats_data = await self.get_task_formats_from_api()
                if formats_data:
                    available_formats = [display_name for display_name, internal_name in formats_data]
                else:
                    available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]
            except Exception:
                available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]

            if text in available_formats:
                await self.admin_handlers.handle_format_selection_text(update, context)
                return

        if admin_task_data and admin_task_data.get('step') == 'title_input':
            # Обрабатываем ввод названия задачи
            await self.admin_handlers.handle_title_input(update, context, text)
            return

        # Обработка создания расходов
        if 'expense_creation' in context.user_data:
            expense_data = context.user_data['expense_creation']

            if text == "/cancel" or text == "❌ Отмена":
                context.user_data.pop('expense_creation', None)
                # Возвращаемся в главное меню
                await self.start_command(update, context)
                return

            if text == "◀️ Назад":
                # Возврат на шаг назад
                current_step = expense_data.get('step')
                if current_step == 'amount':
                    expense_data['step'] = 'name'
                    await self.expense_handlers.handle_add_expense_start(update, context)
                elif current_step == 'project':
                    expense_data['step'] = 'amount'
                    keyboard = [
                        ["◀️ Назад", "❌ Отмена"]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                    message = f"""➕ **Новый расход**

**Шаг 2/5:** Введите сумму расхода

💰 Введите сумму в сумах (только цифры)

📝 Например: 50000"""
                    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
                elif current_step == 'description':
                    expense_data['step'] = 'project'
                    # Показываем выбор проекта заново
                    await self.expense_handlers.show_project_selection(update, context)
                elif current_step == 'date':
                    expense_data['step'] = 'description'
                    # Показываем запрос комментария
                    projects = self.expense_handlers.get_projects()
                    project_name = "Без привязки к проекту"
                    if expense_data.get('project_id'):
                        project = next((p for p in projects if p['id'] == expense_data['project_id']), None)
                        if project:
                            project_name = project['name']

                    keyboard = [
                        ["⏭️ Пропустить"],
                        ["◀️ Назад", "❌ Отмена"]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                    message = f"""➕ **Новый расход**

**Шаг 4/5:** Введите комментарий (необязательно)

📝 **Текущие данные:**
• Наименование: {expense_data['name']}
• Сумма: {expense_data['amount']:,.0f} сум
• Проект: {project_name}

💬 Введите комментарий к расходу"""
                    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
                return

            await self.expense_handlers.handle_expense_text_input(update, context)
            return

        if admin_task_data and admin_task_data.get('step') == 'description_input':
            if text == "📝 Добавить описание":
                # Переходим к вводу описания
                await self.admin_handlers.handle_description_prompt(update, context)
                return
            elif text == "⏭️ Пропустить":
                # Пропускаем описание и переходим к дедлайну
                await self.admin_handlers.handle_deadline_prompt(update, context)
                return
            else:
                # Если пользователь отправил текст вместо нажатия кнопки
                await update.message.reply_text(
                    "⚠️ **Пожалуйста, используйте кнопки ниже для выбора**\n\n"
                    "Нажмите:\n"
                    "• **📝 Добавить описание** - чтобы добавить описание\n"
                    "• **⏭️ Пропустить** - чтобы пропустить этот шаг\n"
                    "• **❌ Отмена** - чтобы отменить создание задачи",
                    parse_mode='Markdown'
                )
                return

        if admin_task_data and admin_task_data.get('step') == 'description_text_input':
            # Обрабатываем ввод описания
            await self.admin_handlers.handle_description_input(update, context, text)
            return

        if admin_task_data and admin_task_data.get('step') == 'deadline_input':
            # Обрабатываем ввод дедлайна
            await self.admin_handlers.handle_deadline_input(update, context, text)
            return

        if admin_task_data and admin_task_data.get('step') == 'final_confirmation':
            if text == "✅ Создать задачу":
                # Создаем задачу
                await self.admin_handlers.create_task(update, context)
                return
            elif text == "✏️ Редактировать":
                # Возвращаем к редактированию
                await self.admin_handlers.handle_edit_task(update, context)
                return

        # Обработка кнопок меню задач
        if text == "➕ Создать задачу":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if db_user and db_user['role'] == 'admin':
                await self.admin_handlers.handle_admin_create_task(update, context)
            elif db_user and db_user['role'] in ['smm_manager', 'designer']:
                await self.user_task_handlers.handle_user_create_task(update, context)
            return

        # Обработка кнопки "Активные задачи" для обычных пользователей
        if text == "📋 Активные задачи":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if db_user and db_user['role'] in ['smm_manager', 'designer']:
                await self.user_task_handlers.handle_active_tasks(update, context)
                return
            # Для админов продолжаем обработку в admin_handlers

        # Обработка кнопки "Завершенные задачи" для обычных пользователей
        if text == "✅ Завершенные задачи":
            user = update.effective_user
            db_user = self.get_user_by_telegram_id(user.id, user.username)
            if db_user and db_user['role'] in ['smm_manager', 'designer']:
                await self.user_task_handlers.handle_completed_tasks(update, context)
            return

        # Обработка кнопки "Не принятые в работу" для всех пользователей
        if text == "🆕 Не принятые в работу":
            await self.admin_handlers.handle_new_tasks_start(update, context)
            return

        elif text in ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер", ]:

            # Проверяем наличие user_task_creation для обычных пользователей
            user_task_data = context.user_data.get('user_task_creation')
            if user_task_data and user_task_data.get('step') == 'role_selection':
                await self.user_task_handlers.handle_role_selection_text(update, context)
                return

            # Получаем данные активных и архивных задач
            active_tasks_data = context.user_data.get('active_tasks_view')
            archived_tasks_data = context.user_data.get('archived_tasks_view')

            # Обработка выбора роли в просмотре архивных задач (приоритет)
            if archived_tasks_data and archived_tasks_data.get('step') == 'role_selection':
                await self.admin_handlers.handle_archived_tasks_role_selection(update, context, text)
                return

            # Обработка выбора роли в просмотре активных задач
            if active_tasks_data and active_tasks_data.get('step') == 'role_selection':
                await self.admin_handlers.handle_active_tasks_role_selection(update, context, text)
                return

            # Обработка выбора роли в создании админских задач
            # Этот блок дублирует обработку выше на строках 1574-1580, удаляем его
            return

        # Обработка выбора исполнителя в админских задачах
        elif admin_task_data and admin_task_data.get('step') == 'executor_selection':
            # Получаем пользователей выбранной роли и проверяем, совпадает ли имя
            users = await self.admin_handlers.get_users_by_role(admin_task_data.get('executor_role'))
            for user in users:
                display_name = user['name']
                if display_name == text:
                    await self.admin_handlers.handle_executor_selection(update, context, text)
                    return

        # Обработка выбора проекта в админских задачах
        elif admin_task_data and admin_task_data.get('step') == 'project_selection':
            projects = await self.admin_handlers.get_all_projects()
            for project in projects:
                if project['name'] == text:
                    await self.admin_handlers.handle_project_selection(update, context, text)
                    return

        # Обработка выбора типа задачи в админских задачах
        elif admin_task_data and admin_task_data.get('step') == 'task_type_selection':
            task_types = self.admin_handlers.get_task_types_by_role(admin_task_data['executor_role'])
            for type_name, type_key in task_types:
                if type_name == text:
                    await self.admin_handlers.handle_task_type_selection(update, context, text)
                    return

        # Обработка выбора формата в админских задачах (для дизайнеров)
        elif admin_task_data and admin_task_data.get('step') == 'format_selection':
            formats = self.admin_handlers.get_formats_for_designer()
            for format_name, format_key in formats:
                if format_name == text:
                    await self.admin_handlers.handle_format_selection(update, context, text)
                    return

        # Обработка администраторских сообщений (включая активные задачи)
        user = update.effective_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)
        if db_user:
            logger.debug(f"User found: {db_user.get('name')}, role: {db_user.get('role')}")

        if db_user and db_user['role'] == 'admin':
            # Пробуем обработать сообщение как администраторское
            result = await self.admin_handlers.handle_admin_message(update, context, text)
            if result:
                return  # Сообщение обработано
            else:
                logger.debug("Admin message not handled by admin_handlers")

        # Обработка кнопок управления задачами для обычных пользователей
        if db_user and db_user['role'] in ['smm_manager', 'designer']:
            # Обработка кнопок "Завершить задачу" и "Удалить задачу"
            if text == "✅ Завершить задачу":
                await self.user_task_handlers.handle_complete_task(update, context)
                return
            elif text == "🗑️ Удалить задачу":
                await self.user_task_handlers.handle_delete_task(update, context)
                return

            # Обработка ввода ID задачи
            if context.user_data.get('awaiting_task_id'):
                handled = await self.user_task_handlers.handle_task_id_input(update, context)
                if handled:
                    return

            # Обработка процесса создания задачи обычными пользователями
            user_task_data = context.user_data.get('user_task_creation')
            if user_task_data:
                step = user_task_data.get('step')

                # Обработка отмены
                if text == "❌ Отмена":
                    context.user_data.pop('user_task_creation', None)
                    await self.user_task_handlers.handle_user_task_management(update, context)
                    return

                # Обработка выбора роли
                if step == 'role_selection':
                    await self.user_task_handlers.handle_role_selection_text(update, context)
                    return
                # Обработка выбора исполнителя
                elif step == 'executor_selection':
                    await self.user_task_handlers.handle_executor_selection_text(update, context)
                    return
                # Обработка ввода названия задачи
                elif step == 'title':
                    await self.user_task_handlers.handle_task_title(update, context)
                    return
                # Обработка ввода описания задачи
                elif step == 'description':
                    await self.user_task_handlers.handle_task_description(update, context)
                    return
                # Обработка выбора проекта
                elif step == 'project':
                    await self.user_task_handlers.handle_task_project(update, context)
                    return
                # Обработка выбора типа задачи
                elif step == 'task_type':
                    await self.user_task_handlers.handle_task_type(update, context)
                    return
                # Обработка выбора формата (для дизайнеров)
                elif step == 'format_selection':
                    await self.user_task_handlers.handle_task_format(update, context)
                    return
                # Обработка выбора дедлайна
                elif step == 'deadline':
                    await self.user_task_handlers.handle_task_deadline(update, context)
                    return
                # Обработка подтверждения создания задачи
                elif step == 'final_confirmation':
                    await self.user_task_handlers.handle_task_confirmation(update, context)
                    return
                # Обработка выбора поля для редактирования
                elif step == 'edit_selection':
                    await self.user_task_handlers.handle_edit_selection(update, context)
                    return

        # Кнопка "Архив задач" обрабатывается в admin_handlers

        # Обработка кнопок создания задач
        if text == "🔙 Отмена":
            # Очищаем данные создания задачи и убираем клавиатуру
            context.user_data.pop('task_creation', None)
            await update.message.reply_text(
                "❌ **Создание задачи отменено**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Проверяем, находится ли пользователь в процессе создания задачи
        task_data = context.user_data.get('task_creation')

        # Обработка выбора роли
        if text in ["🎨 Дизайнер", "📱 СММ-менеджер", ]:
            if not task_data:
                # Инициализируем создание задачи если его нет
                user = update.effective_user
                task_data = self.init_task_creation(user.id)
                context.user_data['task_creation'] = task_data

            # Определяем роль по тексту кнопки
            role_map = {
                "🎨 Дизайнер": "designer",
                "📱 СММ-менеджер": "smm_manager"
            }
            role = role_map[text]
            task_data['role'] = role
            task_data['step'] = 'user_selection'
            context.user_data['task_creation'] = task_data

            await self.handle_user_selection_with_reply(update, context)
            return

        # Обработка выбора пользователя
        if task_data and text.startswith("👤 ") and task_data.get('step') == 'user_selection':
            # Находим выбранного пользователя
            user_name = text.replace("👤 ", "")
            available_users = task_data.get('available_users', [])
            selected_user = None

            for user in available_users:
                if user['name'] == user_name:
                    selected_user = user
                    break

            if selected_user:
                task_data['executor_id'] = selected_user['id']
                task_data['step'] = 'project_selection'
                context.user_data['task_creation'] = task_data
                await self.handle_project_selection_with_reply(update, context)
                return

        # Обработка выбора проекта
        if task_data and text.startswith("📁 ") and task_data.get('step') == 'project_selection':
            # Находим выбранный проект
            project_name = text.replace("📁 ", "")
            available_projects = task_data.get('available_projects', [])
            selected_project = None

            for project in available_projects:
                if project['name'] == project_name:
                    selected_project = project
                    break

            if selected_project:
                task_data['project'] = selected_project['name']
                task_data['project_id'] = selected_project['id']
                task_data['step'] = 'task_type_selection'
                context.user_data['task_creation'] = task_data
                await self.handle_task_type_selection_with_reply(update, context)
                return

        # Обработка выбора типа задачи
        if task_data and task_data.get('step') == 'task_type_selection':
            available_task_types = task_data.get('available_task_types', [])
            selected_task_type = None

            # Найдем выбранный тип задачи
            for task_type in available_task_types:
                if task_type[0] == text:  # task_type[0] - это название с иконкой
                    selected_task_type = task_type[1]  # task_type[1] - это ключ
                    break

            if selected_task_type:
                task_data['task_type'] = selected_task_type
                context.user_data['task_creation'] = task_data

                # Проверяем, нужно ли выбирать формат (только для дизайнеров)
                if task_data.get('role') == 'designer':
                    task_data['step'] = 'format_selection'
                    context.user_data['task_creation'] = task_data
                    await self.handle_format_selection_with_reply(update, context)
                else:
                    # Для не-дизайнеров сразу переходим к вводу названия
                    task_data['step'] = 'awaiting_title_input'
                    context.user_data['task_creation'] = task_data
                    await self.handle_task_details_input_with_reply(update, context)
                return

        # Обработка выбора формата (только для дизайнеров)
        if task_data and task_data.get('step') == 'format_selection':
            available_formats = task_data.get('available_formats', [])
            selected_format = None

            # Найдем выбранный формат
            for format_item in available_formats:
                if format_item[0] == text:  # format_item[0] - это название с иконкой
                    selected_format = format_item[1]  # format_item[1] - это ключ
                    break

            if selected_format:
                task_data['task_format'] = selected_format
                task_data['step'] = 'awaiting_title_input'
                context.user_data['task_creation'] = task_data
                await self.handle_task_details_input_with_reply(update, context)
                return

        # Обработка кнопок в превью задачи
        if task_data and task_data.get('step') == 'task_preview':
            preview_options = task_data.get('preview_options', [])
            if text in preview_options:
                if text == "⏰ Установить дедлайн":
                    await self.handle_set_deadline(update, context)
                    return
                elif text == "✏️ Изменить название":
                    # Возвращаемся к вводу названия
                    task_data['step'] = 'awaiting_title_input'
                    context.user_data['task_creation'] = task_data
                    await self.handle_task_details_input_with_reply(update, context)
                    return
                elif text in ["📝 Добавить описание", "📝 Изменить описание"]:
                    # Переходим к вводу описания
                    await self.handle_description_input(update, context)
                    return
                elif text == "❌ Отмена":
                    # Отменяем создание задачи
                    context.user_data.pop('task_creation', None)
                    await update.message.reply_text(
                        "❌ **Создание задачи отменено**\n\n"
                        "Возвращайтесь, когда будете готовы создать новую задачу!",
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return

        # Обработка выбора дедлайна
        if task_data and task_data.get('step') == 'deadline_selection':
            deadline_options = task_data.get('deadline_options', [])
            if text in deadline_options:
                if text == "🔙 Назад":
                    # Возвращаемся к превью задачи
                    await self.handle_task_preview(update, context)
                    return
                else:
                    # Обрабатываем выбор быстрого дедлайна
                    await self.handle_quick_deadline_selection(update, context, text)
                    return

        # Обработка финального подтверждения
        if task_data and task_data.get('step') == 'final_confirmation':
            confirmation_options = task_data.get('confirmation_options', [])
            if text in confirmation_options:
                if text == "✅ Создать задачу":
                    await self.handle_confirm_task_final(update, context)
                    return
                elif text == "⏰ Изменить дедлайн":
                    await self.handle_set_deadline(update, context)
                    return
                elif text == "✏️ Редактировать":
                    # Возвращаемся к превью задачи
                    await self.handle_task_preview(update, context)
                    return
                elif text == "❌ Отмена":
                    # Отменяем создание задачи
                    context.user_data.pop('task_creation', None)
                    await update.message.reply_text(
                        "❌ **Создание задачи отменено**\n\n"
                        "Возвращайтесь, когда будете готовы создать новую задачу!",
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return

        # Обработка кнопки "Назад"
        if text == "🔙 Назад" and task_data:
            step = task_data.get('step')
            if step == 'user_selection':
                # Возвращаемся к выбору роли
                role_buttons = ["🎨 Дизайнер", "📱 СММ-менеджер", ]
                reply_markup = self.create_reply_keyboard_3_per_row(role_buttons, "🔙 Отмена")
                await update.message.reply_text(
                    "➕ **Создание новой задачи**\n\n"
                    "👥 **Выберите роль исполнителя:**",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                task_data['step'] = 'role_selection'
                context.user_data['task_creation'] = task_data
                return
            elif step == 'project_selection':
                # Возвращаемся к выбору пользователя
                await self.handle_user_selection_with_reply(update, context)
                return
            elif step == 'task_type_selection':
                # Возвращаемся к выбору проекта
                await self.handle_project_selection_with_reply(update, context)
                return
            elif step == 'format_selection':
                # Возвращаемся к выбору типа задачи
                await self.handle_task_type_selection_with_reply(update, context)
                return
            elif step == 'deadline_selection':
                # Возвращаемся к превью задачи
                await self.handle_task_preview(update, context)
                return
            elif step == 'final_confirmation':
                # Возвращаемся к установке дедлайна
                await self.handle_set_deadline(update, context)
                return

        if task_data:
            step = task_data.get('step')

            if step == 'awaiting_title_input':
                # Сохраняем название задачи
                task_data['title'] = update.message.text.strip()
                context.user_data['task_creation'] = task_data

                # Переходим к вводу описания
                await self.handle_description_input(update, context)
                return

            elif step == 'awaiting_description_input':
                # Сохраняем описание задачи
                task_data['description'] = update.message.text.strip()
                context.user_data['task_creation'] = task_data

                # Переходим к установке дедлайна или к preview задачи
                await self.handle_task_preview(update, context)
                return

            elif step == 'awaiting_deadline_input':
                # Обрабатываем ввод дедлайна
                await self.handle_deadline_text_input(update, context)
                return

        # Передаем обработку администраторским обработчикам
        user = update.effective_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)
        if db_user and db_user['role'] == 'admin':
            handled = await self.admin_handlers.handle_text_messages_for_admin(update, context)
            if handled:
                return

        # Не отвечаем на обычные текстовые сообщения, если они не относятся к процессу создания задачи
        # Это предотвращает спам и нежелательные сообщения
        pass

    async def error_handler(self, update: Update, context):
        """Обработчик ошибок"""
        error_message = str(context.error)

        # Игнорируем конфликты 409 - это нормально, если запущен другой экземпляр
        if "409" in error_message or "Conflict" in error_message:
            return  # Не логируем эти ошибки, они не критичны

        # Логируем только серьёзные ошибки
        logger.error(f"Ошибка: {context.error}")
        # Не показываем сообщение об ошибке пользователю - просто логируем

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))

        # Команды с авторизацией
        self.app.add_handler(CommandHandler("tasks", self.tasks_command))
        self.app.add_handler(CommandHandler("projects", self.projects_command))
        self.app.add_handler(CommandHandler("expenses", self.expenses_command))
        self.app.add_handler(CommandHandler("task", self.handle_create_task_start))
        self.app.add_handler(CommandHandler("skip", self.skip_command))

        # Callback кнопки
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))

        # Неизвестные команды и сообщения
        self.app.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_message))

        # Обработчик ошибок
        self.app.add_error_handler(self.error_handler)

        logger.info("✅ Все обработчики настроены")

    # Дополнительные методы для создания задач

    async def handle_project_selection(self, query, context):
        """Обработка выбора проекта"""
        project_id = int(query.data.replace("select_project_", ""))

        # Получаем название проекта из базы
        conn = self.get_db_connection()
        if not conn:
            await query.answer("Ошибка подключения к базе данных")
            return

        cursor = self._execute_query(conn, "SELECT name FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        conn.close()

        if not project:
            await query.answer("Проект не найден")
            return

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['project'] = project['name']
        task_data['step'] = 'task_type_selection'
        context.user_data['task_creation'] = task_data

        # Получаем типы задач из API в зависимости от роли
        role = task_data.get('role')
        task_types = await self.get_task_types_from_api(role)

        # Создаем кнопки данных для типов задач
        buttons_data = [(type_name, f"select_task_type_{type_key}") for type_name, type_key in task_types]

        # Создаем клавиатуру с кнопками по 3 в ряд
        keyboard = self.create_keyboard_3_per_row(
            buttons_data,
            back_button=("🔙 Назад", f"select_user_{task_data['executor_id']}")
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "➕ **Создание новой задачи**\n\n"
            f"📁 **Проект:** {project['name']}\n\n"
            "🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_type_selection_with_reply(self, update, context):
        """Обработка выбора типа задачи с ReplyKeyboard"""
        task_data = context.user_data.get('task_creation', {})
        role = task_data.get('role', '')

        # Получаем типы задач из API
        task_types = await self.get_task_types_from_api(role)

        if not task_types:
            await update.message.reply_text(
                "❌ **Нет доступных типов задач**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Сохраняем типы задач в контексте
        task_data['available_task_types'] = task_types
        context.user_data['task_creation'] = task_data

        # Создаем кнопки с типами задач (убираем иконки для простоты)
        type_buttons = [task_type[0] for task_type in task_types]  # Берем только названия с иконками
        reply_markup = self.create_reply_keyboard_3_per_row(type_buttons, "🔙 Назад")

        await update.message.reply_text(
            "➕ **Создание новой задачи**\n\n"
            "🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_format_selection_with_reply(self, update, context):
        """Обработка выбора формата для дизайнеров с ReplyKeyboard"""
        task_data = context.user_data.get('task_creation', {})

        # Получаем форматы задач из API
        formats = await self.get_task_formats_from_api()

        if not formats:
            await update.message.reply_text(
                "❌ **Нет доступных форматов**",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Сохраняем форматы в контексте
        task_data['available_formats'] = formats
        context.user_data['task_creation'] = task_data

        # Создаем кнопки с форматами
        format_buttons = [format_item[0] for format_item in formats]  # Берем названия с иконками
        reply_markup = self.create_reply_keyboard_3_per_row(format_buttons, "🔙 Назад")

        type_names = {
            'creative': 'Креативная',
            'content': 'Контент',
            'technical': 'Техническая',
            'analytics': 'Аналитическая',
            'communication': 'Общение',
            'video': 'Видео'
        }

        task_type = task_data.get('task_type', '')
        await update.message.reply_text(
            "➕ **Создание новой задачи**\n\n"
            f"🏷️ **Тип:** {type_names.get(task_type, task_type)}\n\n"
            "🎨 **Выберите формат для дизайнера:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_details_input_with_reply(self, update, context):
        """Запрос ввода названия задачи с ReplyKeyboard"""
        task_data = context.user_data.get('task_creation', {})

        # Формируем сообщение с выбранными параметрами
        message = self.get_task_summary_message(task_data)
        message += "\n📝 **Введите название задачи:**"

        # Убираем клавиатуру для ввода текста
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )

    async def handle_task_type_selection(self, query, context):
        """Обработка выбора типа задачи"""
        task_type = query.data.replace("select_task_type_", "")

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['task_type'] = task_type

        # Проверяем, нужно ли выбирать формат (только для дизайнеров)
        if task_data.get('role') == 'designer':
            task_data['step'] = 'format_selection'
            context.user_data['task_creation'] = task_data

            # Получаем форматы задач из API
            formats = await self.get_task_formats_from_api()

            # Создаем кнопки данных для форматов задач
            buttons_data = [(format_name, f"select_format_{format_key}") for format_name, format_key in formats]

            # Создаем клавиатуру с кнопками по 3 в ряд
            keyboard = self.create_keyboard_3_per_row(
                buttons_data,
                back_button=("🔙 Назад", f"select_project_{task_data.get('project_id', 1)}")
            )
            reply_markup = InlineKeyboardMarkup(keyboard)

            type_names = {
                'creative': 'Креативная',
                'content': 'Контент',
                'technical': 'Техническая',
                'analytics': 'Аналитическая',
                'communication': 'Общение',
                'video': 'Видео'
            }

            await query.edit_message_text(
                "➕ **Создание новой задачи**\n\n"
                f"🏷️ **Тип:** {type_names.get(task_type, task_type)}\n\n"
                "🎨 **Выберите формат для дизайнера:**",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # Для не-дизайнеров сразу переходим к вводу названия
            task_data['step'] = 'awaiting_title_input'
            context.user_data['task_creation'] = task_data
            await self.handle_task_details_input(query, context)

    async def handle_format_selection(self, query, context):
        """Обработка выбора формата (только для дизайнеров)"""
        task_format = query.data.replace("select_format_", "")

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['task_format'] = task_format
        task_data['step'] = 'awaiting_title_input'
        context.user_data['task_creation'] = task_data

        await self.handle_task_details_input(query, context)

    async def handle_task_details_input(self, query, context):
        """Запрос ввода названия задачи"""
        task_data = context.user_data.get('task_creation', {})

        # Формируем сообщение с выбранными параметрами
        message = self.get_task_summary_message(task_data)
        message += "\n📝 **Введите название задачи:**"

        # Создаем кнопки навигации
        buttons_data = []
        back_callback = self.get_previous_step_callback(task_data)

        keyboard = self.create_keyboard_3_per_row(
            buttons_data,
            back_button=("🔙 Назад", back_callback)
        )

        # Добавляем кнопку отмены в отдельный ряд
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_task")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Устанавливаем состояние ожидания ввода названия
        task_data['step'] = 'awaiting_title_input'
        context.user_data['task_creation'] = task_data

    async def handle_description_input(self, update, context):
        """Запрос ввода описания задачи"""
        task_data = context.user_data.get('task_creation', {})

        # Формируем сообщение с выбранными параметрами
        message = self.get_task_summary_message(task_data)
        message += f"\n📝 **Название:** {task_data.get('title', 'Не указано')}\n\n"
        message += "📝 **Введите описание задачи (или отправьте /skip для пропуска):**"

        # Создаем кнопки навигации
        buttons_data = [
            ("⏭️ Пропустить", "skip_description"),
        ]

        keyboard = self.create_keyboard_3_per_row(
            buttons_data,
            back_button=("🔙 Назад", "edit_title")
        )

        # Добавляем кнопку отмены в отдельный ряд
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_task")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Устанавливаем состояние ожидания ввода описания
        task_data['step'] = 'awaiting_description_input'
        context.user_data['task_creation'] = task_data

    def get_task_summary_message(self, task_data):
        """Формирует сообщение с выбранными параметрами задачи"""
        role_names = {
            'designer': 'Дизайнер',
            'smm_manager': 'СММ-менеджер',
            'digital': 'Digital'
        }

        message = "➕ **Создание новой задачи**\n\n"
        message += f"👤 **Роль:** {role_names.get(task_data.get('role', ''), task_data.get('role', ''))}\n"
        message += f"📁 **Проект:** {task_data.get('project', '')}\n"
        message += f"🏷️ **Тип:** {task_data.get('task_type', '')}\n"

        if task_data.get('task_format'):
            message += f"🎨 **Формат:** {task_data.get('task_format', '')}\n"

        return message

    def get_previous_step_callback(self, task_data):
        """Определяет callback для кнопки 'Назад' в зависимости от текущего шага"""
        if task_data.get('task_format'):
            # Если есть формат, значит мы от дизайнера и возвращаемся к выбору формата
            return f"select_task_type_{task_data.get('task_type', '')}"
        elif task_data.get('task_type'):
            # Возвращаемся к выбору типа задачи
            return f"select_project_{task_data.get('project_id', 1)}"
        else:
            # Возвращаемся к выбору проекта
            return f"select_user_{task_data.get('executor_id', '')}"

    async def handle_cancel_task(self, query, context):
        """Отмена создания задачи"""
        # Очищаем данные создания задачи
        context.user_data.pop('task_creation', None)

        await query.edit_message_text(
            "❌ **Создание задачи отменено**\n\n"
            "Возвращайтесь, когда будете готовы создать новую задачу!",
            parse_mode='Markdown'
        )

    async def handle_complete_task(self, query, context, task_id):
        """Обработчик завершения задачи"""
        user = query.from_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)

        if not db_user:
            await query.edit_message_text("❌ Необходима авторизация.")
            return

        try:
            # Получаем информацию о задаче
            conn = self.get_db_connection()
            if not conn:
                await query.edit_message_text("❌ Ошибка подключения к базе данных")
                return

            cursor = self._execute_query(conn, "SELECT title, executor_id FROM tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()

            if not task:
                await query.edit_message_text("❌ Задача не найдена")
                return

            # Проверяем права доступа (админ или исполнитель задачи)
            if db_user['role'] != 'admin' and task['executor_id'] != db_user['id']:
                await query.edit_message_text("❌ У вас нет прав для завершения этой задачи")
                return

            # Обновляем статус задачи на "completed"
            self._execute_query(conn, """
                UPDATE tasks
                SET status = 'done', finished_at = datetime('now')
                WHERE id = ?
            """, (task_id,))
            conn.commit()

            await query.edit_message_text(
                f"✅ **Задача завершена!**\n\n"
                f"📝 **{task['title']}**\n"
                f"🎉 Отличная работа!",
                parse_mode='Markdown'
            )

        except Exception as e:
            print(f"Ошибка при завершении задачи: {e}")
            await query.edit_message_text("❌ Ошибка при завершении задачи")
        finally:
            if conn:
                conn.close()

    async def handle_delete_task(self, query, context, task_id):
        """Обработчик удаления задачи"""
        user = query.from_user
        db_user = self.get_user_by_telegram_id(user.id, user.username)

        if not db_user:
            await query.edit_message_text("❌ Необходима авторизация.")
            return

        try:
            # Получаем информацию о задаче
            conn = self.get_db_connection()
            if not conn:
                await query.edit_message_text("❌ Ошибка подключения к базе данных")
                return

            cursor = self._execute_query(conn, "SELECT title, executor_id FROM tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()

            if not task:
                await query.edit_message_text("❌ Задача не найдена")
                return

            # Проверяем права доступа (админ или исполнитель задачи)
            if db_user['role'] != 'admin' and task['executor_id'] != db_user['id']:
                await query.edit_message_text("❌ У вас нет прав для удаления этой задачи")
                return

            # Удаляем задачу
            self._execute_query(conn, "DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

            await query.edit_message_text(
                f"🗑️ **Задача удалена**\n\n"
                f"📝 **{task['title']}**\n"
                f"✅ Задача полностью удалена из системы",
                parse_mode='Markdown'
            )

        except Exception as e:
            print(f"Ошибка при удалении задачи: {e}")
            await query.edit_message_text("❌ Ошибка при удалении задачи")
        finally:
            if conn:
                conn.close()

    async def run(self):
        """Запуск бота"""
        print("🎯 8Bit Task Management System - Telegram Bot", flush=True)
        print("=" * 50, flush=True)
        print(f"🖥️  Платформа: {platform.system()}", flush=True)
        print(f"🐍 Python: {sys.version}", flush=True)
        print(f"📁 База данных: {DATABASE_PATH}", flush=True)
        print(f"🌐 API: {API_BASE_URL}", flush=True)
        print(flush=True)

        if not BOT_TOKEN:
            print("❌ BOT_TOKEN не найден в .env файле", flush=True)
            print("Добавьте токен: BOT_TOKEN=your_token", flush=True)
            return

        print(f"✅ BOT_TOKEN найден (длина: {len(BOT_TOKEN)} символов)", flush=True)

        # Проверка базы данных
        conn = self.get_db_connection()
        if conn:
            print("✅ База данных доступна", flush=True)
            conn.close()
        else:
            print("⚠️  База данных недоступна", flush=True)

        # Проверка API
        try:
            import requests
            response = requests.get(f'{API_BASE_URL}/health', timeout=3)
            print("✅ Backend API доступен" if response.status_code == 200 else "⚠️  Backend API недоступен", flush=True)
        except:
            print("⚠️  Backend API недоступен", flush=True)

        print(flush=True)
        print("🔧 Создание Telegram приложения...", flush=True)

        # Создание приложения
        self.app = Application.builder().token(self.token).build()

        print("📝 Настройка обработчиков...", flush=True)
        self.setup_handlers()

        print("✅ Бот настроен и готов к работе!", flush=True)

        # Очищаем webhook перед запуском polling
        try:
            from telegram import Bot
            bot = Bot(token=self.token)
            await bot.delete_webhook(drop_pending_updates=True)
            print("🔄 Webhook очищен, переключаемся на polling", flush=True)
        except Exception as e:
            print(f"⚠️  Не удалось очистить webhook: {e}", flush=True)

        print("🔗 Найдите бота в Telegram и напишите /start", flush=True)
        print("🛑 Нажмите Ctrl+C для остановки", flush=True)
        print(flush=True)

        try:
            # Запуск с увеличенным таймаутом и интервалом
            await self.app.run_polling(
                drop_pending_updates=True,
                allowed_updates=list(UpdateType),
                poll_interval=1.0,
                timeout=30
            )
        except Exception as e:
            error_msg = str(e)
            if "Conflict" in error_msg and "getUpdates" in error_msg:
                print("❌ Ошибка: Другой экземпляр бота уже получает обновления!")
                print("🔄 Закройте все другие экземпляры бота и попробуйте снова.")
                print("💡 Совет: Проверьте процессы командой: ps aux | grep python")
            else:
                print(f"❌ Ошибка: {error_msg}")
            release_lock()  # Освобождаем блокировку при ошибке

    # ============ TASK CREATION HANDLER METHODS ============

    def create_keyboard_3_per_row(self, buttons_data, back_button=None):
        """Создание клавиатуры с кнопками по 3 в ряд"""
        keyboard = []
        row = []

        for button_text, callback_data in buttons_data:
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем неполный ряд если остались кнопки
        if row:
            keyboard.append(row)

        # Добавляем кнопку "Назад" если указана
        if back_button:
            keyboard.append([InlineKeyboardButton(back_button[0], callback_data=back_button[1])])

        return keyboard

    def create_reply_keyboard_3_per_row(self, buttons_data, back_button_text=None):
        """Создание ReplyKeyboardMarkup с кнопками по 3 в ряд"""
        keyboard = []
        row = []

        for button_text in buttons_data:
            row.append(KeyboardButton(button_text))
            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем неполный ряд если остались кнопки
        if row:
            keyboard.append(row)

        # Добавляем кнопку "Назад" если указана
        if back_button_text:
            keyboard.append([KeyboardButton(back_button_text)])

        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    def get_task_summary_message(self, task_data):
        """Формирование сообщения с текущими параметрами задачи"""
        role_names = {
            'designer': 'Дизайнер',
            'smm_manager': 'СММ-менеджер',
            'digital': 'Digital'
        }

        type_names = {
            'creative': 'Креативная',
            'content': 'Контент',
            'technical': 'Техническая',
            'analytics': 'Аналитическая',
            'communication': 'Общение',
            'video': 'Видео'
        }

        format_names = {
            'static': 'Статика',
            'video': 'Видео',
            'stories': 'Stories',
            'carousel': 'Карусель',
            'presentation': 'Презентация',
            'illustration': 'Иллюстрация'
        }

        message = "➕ **Создание новой задачи**\n\n"
        message += f"👤 **Роль:** {role_names.get(task_data.get('role', ''), task_data.get('role', 'Не выбрано'))}\n"

        if task_data.get('project'):
            message += f"📁 **Проект:** {task_data['project']}\n"

        if task_data.get('task_type'):
            message += f"🏷️ **Тип:** {type_names.get(task_data['task_type'], task_data['task_type'])}\n"

        if task_data.get('task_format'):
            message += f"🎨 **Формат:** {format_names.get(task_data['task_format'], task_data['task_format'])}\n"

        return message

    def get_previous_step_callback(self, task_data):
        """Получение callback для возврата на предыдущий шаг"""
        step = task_data.get('step', '')

        if step == 'user_selection':
            return "create_task"
        elif step == 'project_selection':
            return f"select_role_{task_data.get('role', '')}"
        elif step == 'task_type_selection':
            return f"select_user_{task_data.get('executor_id', '')}"
        elif step == 'format_selection':
            return f"select_project_{task_data.get('project_id', '')}"
        elif step == 'awaiting_title_input':
            if task_data.get('role') == 'designer' and task_data.get('task_format'):
                return f"select_format_{task_data.get('task_format', '')}"
            else:
                return f"select_task_type_{task_data.get('task_type', '')}"
        elif step == 'awaiting_description_input':
            return "edit_title"
        else:
            return "cancel_task"

    async def handle_description_input(self, update, context):
        """Запрос ввода описания задачи"""
        task_data = context.user_data.get('task_creation', {})

        message = self.get_task_summary_message(task_data)
        message += f"\n📝 **Название:** {task_data.get('title', 'Не указано')}\n\n"
        message += "📝 **Введите описание задачи (или нажмите 'Пропустить'):**"

        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_description")],
            [InlineKeyboardButton("✏️ Изменить название", callback_data="edit_title")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_task")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        # Устанавливаем состояние ожидания ввода описания
        task_data['step'] = 'awaiting_description_input'
        context.user_data['task_creation'] = task_data

    async def handle_skip_description(self, query, context):
        """Обработка пропуска описания"""
        task_data = context.user_data.get('task_creation', {})
        task_data['description'] = ''
        task_data['step'] = 'task_preview'
        context.user_data['task_creation'] = task_data

        await self.handle_task_preview(query, context)

    async def handle_edit_title(self, query, context):
        """Обработка редактирования названия"""
        task_data = context.user_data.get('task_creation', {})

        message = self.get_task_summary_message(task_data)
        message += "\n📝 **Введите новое название задачи:**"

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_task")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Устанавливаем состояние ожидания ввода названия
        task_data['step'] = 'awaiting_title_input'
        context.user_data['task_creation'] = task_data

    async def handle_task_preview(self, update, context):
        """Показ превью задачи перед установкой дедлайна"""
        task_data = context.user_data.get('task_creation', {})

        message = self.get_task_summary_message(task_data)
        message += f"\n📝 **Название:** {task_data.get('title', 'Не указано')}"

        description = task_data.get('description', '')
        if description:
            message += f"\n📄 **Описание:** {description}"
        else:
            message += "\n📄 **Описание:** Не указано"

        message += "\n\n✅ **Проверьте данные и продолжите к установке дедлайна:**"

        # Создаем ReplyKeyboard с кнопками действий
        button_options = ["⏰ Установить дедлайн", "✏️ Изменить название"]
        if not description:
            button_options.append("📝 Добавить описание")
        else:
            button_options.append("📝 Изменить описание")

        reply_markup = self.create_reply_keyboard_3_per_row(button_options, "❌ Отмена")

        # Сохраняем опции для обработки в text_message
        task_data['preview_options'] = button_options + ["❌ Отмена"]
        task_data['step'] = 'task_preview'
        context.user_data['task_creation'] = task_data

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_deadline_selection(self, query, context):
        """Обработка выбора быстрого дедлайна"""
        from datetime import datetime, timedelta

        task_data = context.user_data.get('task_creation', {})
        deadline_data = query.data.replace("deadline_", "")

        now = datetime.now()

        if deadline_data == "today_18":
            deadline = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if deadline < now:
                deadline += timedelta(days=1)
        elif deadline_data == "tomorrow_12":
            deadline = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        elif deadline_data == "3days_18":
            deadline = (now + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0)
        elif deadline_data == "week_12":
            deadline = (now + timedelta(days=7)).replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            await query.answer("Неизвестный формат дедлайна")
            return

        task_data['deadline'] = deadline.strftime('%d.%m.%Y %H:%M')
        context.user_data['task_creation'] = task_data

        await self.handle_final_confirmation(query, context)

    async def handle_deadline_text_input(self, update, context):
        """Обработка ввода дедлайна в текстовом формате"""
        from datetime import datetime

        task_data = context.user_data.get('task_creation', {})
        deadline_text = update.message.text.strip()

        try:
            # Пытаемся распарсить дедлайн в формате ДД.ММ.ГГГГ ЧЧ:ММ
            deadline = datetime.strptime(deadline_text, '%d.%m.%Y %H:%M')

            # Проверяем, что дедлайн в будущем
            if deadline < datetime.now():
                await update.message.reply_text(
                    "❌ **Ошибка:** Дедлайн не может быть в прошлом.\n\n"
                    "Введите дедлайн в формате: `ДД.ММ.ГГГГ ЧЧ:ММ`",
                    parse_mode='Markdown'
                )
                return

            task_data['deadline'] = deadline_text
            task_data['step'] = 'final_confirmation'
            context.user_data['task_creation'] = task_data

            await self.handle_final_confirmation(update, context)

        except ValueError:
            await update.message.reply_text(
                "❌ **Ошибка формата дедлайна**\n\n"
                "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\n"
                "**Пример:** `25.12.2024 15:30`",
                parse_mode='Markdown'
            )

    async def handle_final_confirmation(self, update, context):
        """Финальное подтверждение создания задачи"""
        task_data = context.user_data.get('task_creation', {})

        message = "✅ **Подтверждение создания задачи**\n\n"
        message += self.get_task_summary_message(task_data).replace("➕ **Создание новой задачи**\n\n", "")
        message += f"\n📝 **Название:** {task_data.get('title', 'Не указано')}"

        description = task_data.get('description', '')
        if description:
            message += f"\n📄 **Описание:** {description}"

        message += f"\n⏰ **Дедлайн:** {task_data.get('deadline', 'Не установлен')}"
        message += "\n\n**Всё верно? Создать задачу?**"

        # Создаем ReplyKeyboard с кнопками финального подтверждения
        confirmation_options = [
            "✅ Создать задачу",
            "⏰ Изменить дедлайн",
            "✏️ Редактировать"
        ]

        reply_markup = self.create_reply_keyboard_3_per_row(confirmation_options, "❌ Отмена")

        # Сохраняем опции для обработки в text_message
        task_data['confirmation_options'] = confirmation_options + ["❌ Отмена"]
        task_data['step'] = 'final_confirmation'
        context.user_data['task_creation'] = task_data

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def skip_command(self, update: Update, context):
        """Обработка команды /skip"""
        task_data = context.user_data.get('task_creation')
        if task_data and task_data.get('step') == 'awaiting_description_input':
            # Пропускаем описание
            task_data['description'] = ''
            task_data['step'] = 'task_preview'
            context.user_data['task_creation'] = task_data

            await self.handle_task_preview(update, context)
        else:
            await update.message.reply_text(
                "🤖 Используйте /start для просмотра главного меню"
            )

    async def handle_set_deadline(self, update, context):
        """Обработка установки дедлайна"""
        message = (
            "⏰ **Установка дедлайна**\n\n"
            "Введите дедлайн в формате:\n"
            "`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "**Пример:** `25.12.2024 15:30`\n\n"
            "Или выберите быстрые варианты:"
        )

        # Создаем ReplyKeyboard с быстрыми вариантами дедлайна
        deadline_options = [
            "📅 Сегодня 18:00",
            "📅 Завтра 12:00",
            "📅 Через 3 дня 18:00",
            "📅 Через неделю 12:00"
        ]

        reply_markup = self.create_reply_keyboard_3_per_row(deadline_options, "🔙 Назад")

        # Сохраняем опции для обработки в text_message
        task_data = context.user_data.get('task_creation', {})
        task_data['deadline_options'] = deadline_options + ["🔙 Назад"]
        task_data['step'] = 'deadline_selection'
        context.user_data['task_creation'] = task_data

        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

    async def handle_confirm_task(self, query, context):
        """Обработка подтверждения создания задачи"""
        task_data = context.user_data.get('task_creation', {})

        if not task_data:
            await query.answer("Ошибка: данные задачи не найдены")
            return

        try:
            # Создаем задачу в базе данных
            success = await self.create_task_in_database(task_data)

            if success:
                await query.edit_message_text(
                    "✅ **Задача успешно создана!**\n\n"
                    f"📋 **Название:** {task_data.get('title', 'Не указано')}\n"
                    f"📁 **Проект:** {task_data.get('project', 'Не указан')}\n"
                    f"⏰ **Дедлайн:** {task_data.get('deadline', 'Не установлен')}\n\n"
                    "Задача отображается в системе и доступна исполнителю.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Ошибка при создании задачи**\n\n"
                    "Попробуйте создать задачу заново или обратитесь к администратору.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            await query.edit_message_text(
                "❌ **Произошла ошибка при создании задачи**\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode='Markdown'
            )
        finally:
            # Очищаем данные создания задачи
            context.user_data.pop('task_creation', None)

    async def handle_cancel_task(self, query, context):
        """Отмена создания задачи"""
        # Очищаем данные создания задачи
        context.user_data.pop('task_creation', None)

        await query.edit_message_text(
            "❌ **Создание задачи отменено**\n\n"
            "Возвращайтесь, когда будете готовы создать новую задачу!",
            parse_mode='Markdown'
        )

    async def create_task_in_database(self, task_data):
        """Создание задачи в базе данных"""
        try:
            import requests
            from datetime import datetime

            # Получаем информацию об авторе задачи
            author_user = self.get_user_by_telegram_id(task_data['user_id'], None)
            if not author_user:
                return False

            # Формируем данные для создания задачи
            payload = {
                'title': task_data.get('title', 'Новая задача'),
                'description': task_data.get('description', ''),
                'project': task_data.get('project', ''),
                'task_type': task_data.get('task_type', ''),
                'task_format': task_data.get('task_format', ''),
                'executor_id': task_data.get('executor_id'),
                'author_id': author_user['id'],
                'deadline': task_data.get('deadline')
            }

            # Отправляем запрос к API
            response = requests.post(
                f'{API_BASE_URL}/tasks/',
                json=payload,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Ошибка создания задачи в БД: {e}")
            return False

    async def handle_quick_deadline_selection(self, update, context, deadline_text):
        """Обработка выбора быстрого дедлайна"""
        from datetime import datetime, timedelta

        task_data = context.user_data.get('task_creation', {})
        now = datetime.now()

        if deadline_text == "📅 Сегодня 18:00":
            deadline = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if deadline < now:
                deadline += timedelta(days=1)
        elif deadline_text == "📅 Завтра 12:00":
            deadline = (now + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        elif deadline_text == "📅 Через 3 дня 18:00":
            deadline = (now + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0)
        elif deadline_text == "📅 Через неделю 12:00":
            deadline = (now + timedelta(days=7)).replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            await update.message.reply_text(
                "❌ Неизвестный формат дедлайна",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        task_data['deadline'] = deadline.strftime('%d.%m.%Y %H:%M')
        context.user_data['task_creation'] = task_data

        await self.handle_final_confirmation(update, context)

    async def handle_confirm_task_final(self, update, context):
        """Финальное создание задачи"""
        task_data = context.user_data.get('task_creation', {})

        if not task_data:
            await update.message.reply_text(
                "❌ Ошибка: данные задачи не найдены",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        try:
            # Создаем задачу в базе данных
            success = await self.create_task_in_database(task_data)

            if success:
                await update.message.reply_text(
                    "✅ **Задача успешно создана!**\n\n"
                    f"📋 **Название:** {task_data.get('title', 'Не указано')}\n"
                    f"📁 **Проект:** {task_data.get('project', 'Не указан')}\n"
                    f"⏰ **Дедлайн:** {task_data.get('deadline', 'Не установлен')}\n\n"
                    "Задача отображается в системе и доступна исполнителю.",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text(
                    "❌ **Ошибка при создании задачи**\n\n"
                    "Попробуйте создать задачу заново или обратитесь к администратору.",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            await update.message.reply_text(
                "❌ **Произошла ошибка при создании задачи**\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
        finally:
            # Очищаем данные создания задачи
            context.user_data.pop('task_creation', None)

async def main():
    """Главная функция"""
    bot = TelegramBot(BOT_TOKEN)

    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            await bot.run()
            break  # Если успешно, выходим из цикла
        except KeyboardInterrupt:
            print("\n🛑 Остановка бота...", flush=True)
            release_lock()
            break
        except Exception as e:
            if "409 Conflict" in str(e) or "Conflict" in str(e):
                retry_count += 1
                wait_time = retry_count * 15  # Увеличиваем время ожидания
                print(f"\n⚠️  Конфликт с другим экземпляром бота (попытка {retry_count}/{max_retries})", flush=True)
                print(f"⏳ Ожидание {wait_time} секунд перед повторной попыткой...", flush=True)
                await asyncio.sleep(wait_time)

                if retry_count >= max_retries:
                    print("❌ Превышено максимальное количество попыток. Возможно, другой экземпляр бота всё ещё работает.", flush=True)
                    print("💡 Попробуйте остановить все экземпляры бота и запустить заново.", flush=True)
                    release_lock()
                    break
            else:
                # Если это не конфликт, выводим ошибку и завершаем
                print(f"❌ Ошибка: {e}", flush=True)
                import traceback
                traceback.print_exc()
                release_lock()
                break

    release_lock()  # Убедимся, что блокировка освобождена
    print("👋 Бот остановлен!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())