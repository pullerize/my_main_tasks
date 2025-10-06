"""
Обработчики администраторских функций для создания и управления задачами
"""

import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

logger = logging.getLogger(__name__)

class AdminTaskHandlers:
    """Класс для обработки администраторских функций"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    def _execute_query(self, conn, query: str, params: tuple):
        """
        Вспомогательная функция для выполнения SQL запросов
        с автоматическим определением типа БД (SQLite или PostgreSQL)
        """
        import os
        db_engine = os.getenv('DB_ENGINE', 'sqlite').lower()

        if db_engine == 'postgresql':
            # PostgreSQL: создаем курсор и используем %s для параметров
            cursor = conn.cursor()
            # Заменяем ? на %s для PostgreSQL
            pg_query = query.replace('?', '%s')
            # Заменяем is_active = 1 на is_active = true для PostgreSQL
            pg_query = pg_query.replace('is_active = 1', 'is_active = true')
            pg_query = pg_query.replace('is_active = 0', 'is_active = false')
            cursor.execute(pg_query, params)
            return cursor
        else:
            # SQLite: используем execute напрямую с ?
            return conn.execute(query, params)

    async def handle_admin_task_management(self, update, context):
        """Меню управления задачами для администратора"""
        keyboard = [
            ["➕ Создать задачу"],
            ["📋 Активные задачи", "📁 Архив задач"],
            ["🆕 Не принятые в работу"],
            ["🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "🔧 **Управление задачами** 🔧\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_admin_create_task(self, update, context):
        """Начало создания задачи администратором с выбором роли"""
        # Инициализируем создание задачи
        context.user_data['admin_task_creation'] = {
            'creator_id': update.message.from_user.id,
            'step': 'role_selection'
        }

        # Создаем обычные кнопки клавиатуры с ролями (по 3 в ряд)
        keyboard = [
            ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "➕ **Создание новой задачи**\n\n"
            "👥 **Выберите роль исполнителя:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_role_selection_text(self, update, context):
        """Обработка выбора роли исполнителя через текстовое сообщение"""
        message_text = update.message.text

        # Сопоставление текста кнопок с ролями
        role_mapping = {
            "🔑 Администратор": "admin",
            "📱 СММ-менеджер": "smm_manager",
            "🎨 Дизайнер": "designer"
        }

        role = role_mapping.get(message_text)
        if not role:
            return


        # Продолжаем с той же логикой, что и в callback версии
        await self._process_role_selection(update, context, role, is_callback=False)

    async def handle_role_selection(self, query, context):
        """Обработка выбора роли исполнителя через callback query"""
        # Извлекаем роль из callback data
        role = query.data.replace("select_role_", "")

        # Проверяем корректность роли
        valid_roles = ['admin', 'designer', 'smm_manager', 'digital']
        if role not in valid_roles:
            await query.answer("❌ Неверная роль")
            return


        # Продолжаем с той же логикой
        await self._process_role_selection(query, context, role, is_callback=True)

    async def handle_executor_selection_text(self, update, context):
        """Обработка выбора исполнителя через текстовое сообщение"""
        message_text = update.message.text

        # Извлекаем имя исполнителя из текста кнопки
        if not message_text.startswith("👤 "):
            return

        executor_name = message_text[2:].strip()  # Убираем "👤 " в начале

        # Получаем данные задачи
        task_data = context.user_data.get('admin_task_creation', {})
        role = task_data.get('executor_role')

        if not role:
            return

        # Получаем всех пользователей этой роли из кеша или запрашиваем заново
        users = task_data.get('_cached_users')
        if not users:
            users = await self.get_users_by_role(role)

        # Ищем пользователя по имени (точное совпадение)
        executor = None
        for user in users:
            if user['name'].strip() == executor_name.strip():
                executor = user
                break

        if not executor:
            await update.message.reply_text(
                f"❌ Исполнитель не найден\n\n"
                f"Попробуйте выбрать из предложенных кнопок."
            )
            return


        # Обновляем данные создания задачи
        task_data['executor_id'] = executor['id']
        task_data['executor_name'] = executor['name']

        # Проверяем, нужно ли вернуться к предпросмотру
        if task_data.get('return_to_preview'):
            task_data['step'] = 'final_confirmation'
            task_data.pop('return_to_preview', None)
            context.user_data['admin_task_creation'] = task_data
            await self.show_task_preview(update, context)
            return

        task_data['step'] = 'project_selection'
        context.user_data['admin_task_creation'] = task_data

        # Получаем все проекты и кешируем
        projects = await self.get_all_projects()

        if not projects:
            await update.message.reply_text(
                f"❌ **Нет доступных проектов**\n\n"
                "Обратитесь к администратору для создания проектов.",
                parse_mode='Markdown'
            )
            return

        # Сохраняем проекты в кеш для избежания повторных запросов
        task_data['_cached_projects'] = projects
        context.user_data['admin_task_creation'] = task_data

        # Создаем обычные кнопки клавиатуры с проектами (по 2 в ряд)
        keyboard = []
        project_buttons = [f"📁 {project['name'].strip()}" for project in projects]
        for i in range(0, len(project_buttons), 2):
            row = project_buttons[i:i+2]
            keyboard.append(row)

        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {executor['name']}\n\n"
            f"📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_project_selection_text(self, update, context):
        """Обработка выбора проекта через текстовое сообщение"""
        message_text = update.message.text
        logger.debug(f"Project selection text: '{message_text}'")

        # Извлекаем название проекта из текста кнопки
        if not message_text.startswith("📁 "):
            logger.warning(f"Invalid project text format: '{message_text}'")
            return

        project_name = message_text[2:].strip()  # Убираем "📁 " в начале

        # Валидация пустого имени проекта
        if not project_name:
            logger.warning("Empty project name after emoji removal")
            await update.message.reply_text("❌ Некорректное имя проекта")
            return

        # Используем кешированные проекты если есть
        task_data = context.user_data.get('admin_task_creation', {})
        projects = task_data.get('_cached_projects')

        if not projects:
            # Если кеша нет, запрашиваем и сохраняем
            projects = await self.get_all_projects()
            task_data['_cached_projects'] = projects

        # Оптимизированный поиск через словарь O(1) вместо O(n)
        projects_map = {p['name'].strip(): p for p in projects}
        project = projects_map.get(project_name.strip())

        if not project:
            logger.warning(f"Project '{project_name}' not found in {list(projects_map.keys())}")
            await update.message.reply_text("❌ Проект не найден")
            return

        logger.info(f"Found project: {project['name']} (id={project['id']})")

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['project_id'] = project['id']
        task_data['project_name'] = project['name']
        task_data['step'] = 'task_type_selection'
        context.user_data['admin_task_creation'] = task_data

        # Получаем роль исполнителя для определения доступных типов задач
        executor_role = task_data.get('executor_role')

        # Получаем типы задач для роли из приложения
        task_types = await self.get_task_types_by_role(executor_role)

        if not task_types:
            await update.message.reply_text("❌ Нет доступных типов задач для этой роли")
            return

        # Создаем обычные кнопки клавиатуры с типами задач (по 3 в ряд)
        keyboard = []
        for i in range(0, len(task_types), 3):
            row = task_types[i:i+3]
            keyboard.append(row)
        keyboard.append(["🔙 Назад"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {task_data.get('executor_name', 'Не указан')}\n"
            f"📁 **Проект:** {project['name']}\n\n"
            f"🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_type_selection_text(self, update, context):
        """Обработка выбора типа задачи через текстовое сообщение"""
        message_text = update.message.text

        task_data = context.user_data.get('admin_task_creation', {})
        executor_role = task_data.get('executor_role')

        # Получаем доступные типы задач для роли из API
        available_task_types = await self.get_task_types_by_role(executor_role)

        if message_text not in available_task_types:
            return


        # Обновляем данные создания задачи
        task_data['task_type'] = message_text  # Сохраняем полное название как было выбрано
        context.user_data['admin_task_creation'] = task_data

        # Проверяем, нужно ли выбирать формат для дизайнеров
        if executor_role == 'designer':
            task_data['step'] = 'format_selection'
            context.user_data['admin_task_creation'] = task_data

            # Показываем выбор формата для дизайнеров
            await self.show_format_selection(update, context)
        else:
            # Для других ролей сразу переходим к вводу названия
            task_data['step'] = 'title_input'
            context.user_data['admin_task_creation'] = task_data

            # Убираем кнопки предыдущего шага и показываем только кнопку Отмена
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

    async def show_format_selection(self, update, context):
        """Показать выбор формата для дизайнеров"""
        task_data = context.user_data.get('admin_task_creation', {})

        # Получаем форматы для дизайнеров из API
        try:
            formats_data = await self.bot.get_task_formats_from_api()
            if formats_data:
                # API возвращает список кортежей: [(display_name, internal_name), ...]
                formats = [display_name for display_name, internal_name in formats_data]
            else:
                # Fallback к статическим форматам
                formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]
        except Exception as e:
            # Fallback к статическим форматам
            formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]

        # Создаем обычные кнопки клавиатуры с форматами (по 3 в ряд)
        keyboard = []
        for i in range(0, len(formats), 3):
            row = formats[i:i+3]
            keyboard.append(row)

        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {task_data.get('executor_name', 'Не указан')}\n"
            f"📁 **Проект:** {task_data.get('project_name', 'Не указан')}\n"
            f"🏷️ **Тип:** {task_data.get('task_type', 'Не указан')}\n\n"
            f"🎨 **Выберите формат для дизайнера:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_format_selection_text(self, update, context):
        """Обработка выбора формата через текстовое сообщение"""
        message_text = update.message.text

        # Получаем доступные форматы из API
        try:
            formats_data = await self.bot.get_task_formats_from_api()
            if formats_data:
                available_formats = [display_name for display_name, internal_name in formats_data]
            else:
                available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]
        except Exception as e:
            available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]

        if message_text not in available_formats:
            return


        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['format'] = message_text  # Сохраняем полное название формата
        task_data['step'] = 'title_input'
        context.user_data['admin_task_creation'] = task_data

        # Убираем кнопки предыдущего шага (форматы) и показываем только кнопку Отмена
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

    async def start_title_input_OLD(self, update, context):
        """Начало ввода названия задачи (старая версия, не используется)"""
        task_data = context.user_data.get('admin_task_creation', {})

        # Убираем кнопки клавиатуры для ввода текста
        reply_markup = ReplyKeyboardRemove()

        # Получаем читаемое название типа задачи
        task_type_names = {
            "creative": "Креативная",
            "content": "Контент",
            "technical": "Техническая",
            "analytics": "Аналитическая",
            "communication": "Общение",
            "video": "Видео"
        }

        task_type_name = task_type_names.get(task_data.get('task_type', ''), 'Не указан')

        await update.message.reply_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {task_data.get('executor_name', 'Не указан')}\n"
            f"📁 **Проект:** {task_data.get('project_name', 'Не указан')}\n"
            f"🏷️ **Тип:** {task_type_name}\n\n"
            f"📝 **Введите название задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _process_role_selection(self, update_or_query, context, role, is_callback=True, page=0):
        """Общая логика обработки выбора роли"""

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['executor_role'] = role
        task_data['step'] = 'executor_selection'
        context.user_data['admin_task_creation'] = task_data

        # Получаем пользователей этой роли
        users = await self.get_users_by_role(role)

        if not users:
            message_text = (
                f"❌ **Нет доступных исполнителей с ролью:** {self.get_role_name(role)}\n\n"
                "Попробуйте выбрать другую роль."
            )

            if is_callback:
                await update_or_query.edit_message_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Назад", callback_data="admin_create_task")
                    ]])
                )
            else:
                await update_or_query.message.reply_text(
                    message_text,
                    parse_mode='Markdown'
                )
            return

        # Кешируем всех пользователей
        task_data['_cached_users'] = users
        context.user_data['admin_task_creation'] = task_data

        # Создаем обычные кнопки клавиатуры (по 3 в ряд)
        keyboard = []
        row = []
        for user in users:
            row.append(f"👤 {user['name']}")
            if len(row) == 3:
                keyboard.append(row)
                row = []

        # Добавляем оставшиеся кнопки
        if row:
            keyboard.append(row)

        # Добавляем кнопку "Назад"
        keyboard.append(["🔙 Назад"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        role_name = self.get_role_name(role)
        message_text = (
            f"➕ **Создание новой задачи**\n\n"
            f"👥 **Роль:** {role_name}\n\n"
            f"👤 **Выберите исполнителя:**"
        )

        if is_callback:
            # Для callback query отправляем новое сообщение с клавиатурой
            await update_or_query.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update_or_query.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    async def handle_executor_page(self, query, context):
        """Обработка переключения страниц исполнителей"""
        # Формат: executor_page_{role}_{page}
        parts = query.data.replace("executor_page_", "").split("_")
        if len(parts) < 2:
            await query.answer("❌ Ошибка формата данных")
            return

        role = parts[0]
        try:
            page = int(parts[1])
        except ValueError:
            await query.answer("❌ Неверный номер страницы")
            return

        await self._process_role_selection(query, context, role, is_callback=True, page=page)

    async def handle_executor_selection(self, query, context):
        """Обработка выбора исполнителя через callback query"""
        # Извлекаем ID исполнителя из callback data
        executor_id = int(query.data.replace("select_executor_", ""))

        task_data = context.user_data.get('admin_task_creation', {})
        users = await self.get_users_by_role(task_data.get('executor_role'))

        # Находим пользователя по ID
        executor = None
        for user in users:
            if user['id'] == executor_id:
                executor = user
                break

        if not executor:
            await query.answer("❌ Исполнитель не найден")
            return

        # Обновляем данные создания задачи
        task_data['executor_id'] = executor['id']
        task_data['executor_name'] = executor['name']
        task_data['step'] = 'project_selection'

        # Получаем все проекты и кешируем в context
        projects = await self.get_all_projects()
        task_data['_cached_projects'] = projects  # Кеш для избежания повторных запросов

        context.user_data['admin_task_creation'] = task_data

        if not projects:
            await query.edit_message_text(
                "❌ **Нет доступных проектов**\n\n"
                "Обратитесь к администратору для создания проектов.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад", callback_data=f"select_role_{task_data.get('executor_role')}")
                ]])
            )
            return

        # Создаем inline кнопки с пагинацией (10 на страницу)
        PAGE_SIZE = 10
        total_pages = (len(projects) - 1) // PAGE_SIZE + 1
        page = 0  # Первая страница
        start_idx = page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, len(projects))

        keyboard = []
        for project in projects[start_idx:end_idx]:
            keyboard.append([InlineKeyboardButton(
                f"📁 {project['name']}",
                callback_data=f"select_project_{project['id']}"
            )])

        # Добавляем кнопки навигации если нужно
        nav_buttons = []
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"project_page_{page+1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_role_{task_data.get('executor_role')}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        page_info = f" (стр. {page+1}/{total_pages})" if total_pages > 1 else ""
        await query.edit_message_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {executor['name']}{page_info}\n\n"
            f"📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_project_page(self, query, context):
        """Обработка переключения страниц проектов"""
        # Формат: project_page_{page}
        try:
            page = int(query.data.replace("project_page_", ""))
        except ValueError:
            await query.answer("❌ Неверный номер страницы")
            return

        task_data = context.user_data.get('admin_task_creation', {})
        projects = task_data.get('_cached_projects', [])

        if not projects:
            projects = await self.get_all_projects()
            task_data['_cached_projects'] = projects

        # Создаем inline кнопки с пагинацией (10 на страницу)
        PAGE_SIZE = 10
        total_pages = (len(projects) - 1) // PAGE_SIZE + 1
        start_idx = page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, len(projects))

        keyboard = []
        for project in projects[start_idx:end_idx]:
            keyboard.append([InlineKeyboardButton(
                f"📁 {project['name']}",
                callback_data=f"select_project_{project['id']}"
            )])

        # Добавляем кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"project_page_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"project_page_{page+1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton("🔙 К исполнителям", callback_data=f"select_role_{task_data.get('executor_role')}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        page_info = f" (стр. {page+1}/{total_pages})" if total_pages > 1 else ""
        await query.edit_message_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {task_data.get('executor_name', 'Не выбран')}{page_info}\n\n"
            f"📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_project_selection(self, query, context):
        """Обработка выбора проекта через callback query"""
        # Извлекаем ID проекта из callback data
        project_id = int(query.data.replace("select_project_", ""))

        task_data = context.user_data.get('admin_task_creation', {})

        # Используем кешированные проекты вместо повторного запроса
        projects = task_data.get('_cached_projects', [])
        if not projects:
            # Если кеш пустой, запрашиваем заново
            projects = await self.get_all_projects()

        # Находим проект по ID
        project = None
        for proj in projects:
            if proj['id'] == project_id:
                project = proj
                break

        if not project:
            await query.answer("❌ Проект не найден")
            return

        # Обновляем данные создания задачи
        task_data['project_id'] = project['id']
        task_data['project_name'] = project['name']
        task_data['step'] = 'task_type_selection'
        context.user_data['admin_task_creation'] = task_data

        # Получаем типы задач для выбранной роли
        task_types = self.get_task_types_by_role(task_data['executor_role'])

        # Создаем inline кнопки с типами задач
        keyboard = []
        for type_name, type_key in task_types:
            keyboard.append([InlineKeyboardButton(
                f"🏷️ {type_name}",
                callback_data=f"select_task_type_{type_key}"
            )])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_executor_{task_data['executor_id']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {task_data['executor_name']}\n"
            f"📁 **Проект:** {project['name']}\n\n"
            f"🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_type_selection(self, query, context):
        """Обработка выбора типа задачи через callback query"""
        # Извлекаем тип задачи из callback data
        task_type = query.data.replace("select_task_type_", "")

        task_data = context.user_data.get('admin_task_creation', {})

        # Проверяем корректность типа задачи
        task_types = await self.get_task_types_by_role(task_data['executor_role'])

        if task_type not in task_types:
            await query.answer("❌ Неверный тип задачи")
            return

        # Обновляем данные создания задачи
        task_data['task_type'] = task_type
        task_data['step'] = 'format_selection' if task_data['executor_role'] == 'designer' else 'title_input'
        context.user_data['admin_task_creation'] = task_data

        # Если дизайнер, показываем выбор формата
        if task_data['executor_role'] == 'designer':
            formats = self.get_formats_for_designer()

            keyboard = []
            for format_name, format_key in formats:
                keyboard.append([InlineKeyboardButton(
                    f"📐 {format_name}",
                    callback_data=f"select_format_{format_key}"
                )])

            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_project_{task_data['project_id']}")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"➕ **Создание новой задачи**\n\n"
                f"👤 **Исполнитель:** {task_data['executor_name']}\n"
                f"📁 **Проект:** {task_data['project_name']}\n"
                f"🏷️ **Тип:** {self.get_task_type_name(task_type)}\n\n"
                f"📐 **Выберите формат:**",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # Переходим к вводу названия
            await self.start_title_input(query, context)

    async def handle_format_selection(self, query, context):
        """Обработка выбора формата (для дизайнеров) через callback query"""
        # Извлекаем формат из callback data
        format_type = query.data.replace("select_format_", "")

        # Проверяем корректность формата
        formats = self.get_formats_for_designer()
        valid_formats = [format_key for format_name, format_key in formats]

        if format_type not in valid_formats:
            await query.answer("❌ Неверный формат")
            return

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['format'] = format_type
        task_data['step'] = 'title_input'
        context.user_data['admin_task_creation'] = task_data

        # Переходим к вводу названия
        await self.start_title_input(query, context)

    async def start_title_input(self, query, context):
        """Переход к вводу названия задачи"""
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['step'] = 'title_input'
        context.user_data['admin_task_creation'] = task_data

        # Используем inline кнопку для отмены
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="admin_create_task")
        ]])

        await query.edit_message_text(
            "➕ **Создание новой задачи**\n\n"
            "📝 **Название задачи:**\n\n"
            "Напишите краткое и понятное название в следующем сообщении.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def handle_title_input(self, update, context, title):
        """Обработка ввода названия задачи"""
        if len(title) < 3:
            await update.message.reply_text(
                "❌ **Название слишком короткое**\n\n"
                "Название должно содержать минимум 3 символа.\n"
                "Попробуйте еще раз:",
                parse_mode='Markdown'
            )
            return

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['title'] = title

        # Проверяем, возвращаемся ли мы к предпросмотру после редактирования
        if task_data.get('return_to_preview'):
            task_data['step'] = 'final_confirmation'
            task_data.pop('return_to_preview', None)
            context.user_data['admin_task_creation'] = task_data
            await self.show_task_preview(update, context)
            return

        task_data['step'] = 'description_input'
        context.user_data['admin_task_creation'] = task_data

        # Создаем клавиатуру для выбора: добавить описание или пропустить
        # input_field_placeholder скрывает подсказку ввода текста
        keyboard = ReplyKeyboardMarkup(
            [
                ["📝 Добавить описание", "⏭️ Пропустить"],
                ["❌ Отмена"]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
            input_field_placeholder="Используйте кнопки ниже"
        )

        await update.message.reply_text(
            f"✅ **Название сохранено:** {title}\n\n"
            f"📝 **Хотите добавить описание к задаче?**\n\n"
            f"⚠️ **Используйте только кнопки ниже для выбора**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def handle_description_prompt(self, update, context):
        """Переход к вводу описания"""
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['step'] = 'description_text_input'
        context.user_data['admin_task_creation'] = task_data

        # Убираем reply клавиатуру
        keyboard = ReplyKeyboardMarkup(
            [["❌ Отмена"]],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await update.message.reply_text(
            "📝 **Введите описание задачи:**\n\n"
            "Опишите подробности, требования или дополнительную информацию.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def handle_description_input(self, update, context, description):
        """Обработка ввода описания"""
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['description'] = description
        context.user_data['admin_task_creation'] = task_data

        await update.message.reply_text(
            f"✅ **Описание сохранено**\n\n"
            f"📋 **Описание:** {description[:100]}{'...' if len(description) > 100 else ''}",
            parse_mode='Markdown'
        )

        # Переходим к установке дедлайна
        await self.handle_deadline_prompt(update, context)

    async def handle_deadline_prompt(self, update, context):
        """Переход к установке дедлайна"""
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['step'] = 'deadline_input'
        context.user_data['admin_task_creation'] = task_data

        keyboard = ReplyKeyboardMarkup(
            [
                ["📅 Сегодня до 18:00"],
                ["🌆 Завтра до 18:00"],
                ["📆 Через неделю до 18:00"],
                ["❌ Отмена"]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await update.message.reply_text(
            "⏰ **Установите дедлайн для задачи:**\n\n"
            "Введите дату и время в формате:\n"
            "• `18.09.2025 18:00`\n\n"
            "Или выберите один из быстрых вариантов ниже:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def handle_deadline_input(self, update, context, deadline_text):
        """Обработка ввода дедлайна"""
        task_data = context.user_data.get('admin_task_creation', {})

        if deadline_text == "📅 Сегодня до 18:00":
            # Устанавливаем дедлайн на сегодня 18:00 в локальном времени
            local_now = datetime.now()
            today_18_local = local_now.replace(hour=18, minute=0, second=0, microsecond=0)
            # Сохраняем локальное время как есть
            task_data['deadline'] = today_18_local
            task_data['deadline_text'] = today_18_local.strftime("%d.%m.%Y %H:%M")
        elif deadline_text == "🌆 Завтра до 18:00":
            # Устанавливаем дедлайн на завтра 18:00 в локальном времени
            local_now = datetime.now()
            tomorrow_18_local = (local_now + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
            # Сохраняем локальное время как есть
            task_data['deadline'] = tomorrow_18_local
            task_data['deadline_text'] = tomorrow_18_local.strftime("%d.%m.%Y %H:%M")
        elif deadline_text == "📆 Через неделю до 18:00":
            # Устанавливаем дедлайн через неделю в 18:00 в локальном времени
            local_now = datetime.now()
            week_later_18_local = (local_now + timedelta(days=7)).replace(hour=18, minute=0, second=0, microsecond=0)
            # Сохраняем локальное время как есть
            task_data['deadline'] = week_later_18_local
            task_data['deadline_text'] = week_later_18_local.strftime("%d.%m.%Y %H:%M")
        else:
            # Парсим дедлайн
            deadline = self.parse_deadline(deadline_text)
            if deadline:
                task_data['deadline'] = deadline
                # Дедлайн уже в локальном времени, просто форматируем для отображения
                task_data['deadline_text'] = deadline.strftime("%d.%m.%Y %H:%M")
            else:
                await update.message.reply_text(
                    "❌ **Неверный формат даты**\n\n"
                    "Используйте формат: `18.09.2025 18:00`\n"
                    "Попробуйте еще раз:",
                    parse_mode='Markdown'
                )
                return

        context.user_data['admin_task_creation'] = task_data

        # Показываем предварительный просмотр задачи
        await self.show_task_preview(update, context)

    def parse_deadline(self, deadline_text):
        """Парсинг дедлайна из текста"""
        try:
            # Пробуем различные форматы
            formats = [
                "%d.%m.%Y %H:%M",
                "%d.%m.%Y %H.%M",
                "%d.%m.%Y",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y"
            ]

            for fmt in formats:
                try:
                    if fmt.endswith("%H:%M") or fmt.endswith("%H.%M"):
                        local_dt = datetime.strptime(deadline_text, fmt)
                        # Возвращаем локальное время как есть
                        return local_dt
                    else:
                        # Если время не указано, ставим 23:59 локального времени
                        local_dt = datetime.strptime(deadline_text, fmt).replace(hour=23, minute=59)
                        # Возвращаем локальное время как есть
                        return local_dt
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    async def show_task_preview(self, update, context):
        """Показ предварительного просмотра задачи"""
        task_data = context.user_data.get('admin_task_creation', {})

        # Формируем красивый вывод
        preview_text = f"""
📋 **Предварительный просмотр задачи**

┌─────────────────────────────────┐
│ 📝 **Название:** {task_data.get('title', 'Не указано')}
│ 👤 **Исполнитель:** {task_data.get('executor_name', 'Не выбран')}
│ 📁 **Проект:** {task_data.get('project_name', 'Не выбран')}
│ 🏷️ **Тип:** {self.get_task_type_name(task_data.get('task_type', ''))}
"""

        if task_data.get('format'):
            preview_text += f"│ 📐 **Формат:** {task_data.get('format')}\n"

        preview_text += f"│ ⏰ **Дедлайн:** {task_data.get('deadline_text', 'Не установлен')}\n"

        if task_data.get('description'):
            desc = task_data['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            preview_text += f"│ 📄 **Описание:** {desc}\n"

        preview_text += "└─────────────────────────────────┘"

        keyboard = ReplyKeyboardMarkup(
            [
                ["✅ Создать задачу"],
                ["✏️ Редактировать", "❌ Отмена"]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

        await update.message.reply_text(
            preview_text,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

        # Обновляем шаг
        task_data['step'] = 'final_confirmation'
        context.user_data['admin_task_creation'] = task_data

    async def create_task(self, update, context):
        """Создание задачи в базе данных"""
        task_data = context.user_data.get('admin_task_creation', {})

        try:
            # Получаем подключение к БД
            conn = self.bot.get_db_connection()
            if not conn:
                await update.message.reply_text(
                    "❌ **Ошибка подключения к базе данных**",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Получаем данные создателя задачи
            creator = self.bot.get_user_by_telegram_id(task_data['creator_id'], None)
            if not creator:
                await update.message.reply_text(
                    "❌ **Ошибка: создатель не найден**",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Создаем задачу в БД
            # Получаем название проекта по ID
            project_name = None
            if task_data.get('project_id'):
                project = await self.get_project_by_id(task_data.get('project_id'))
                if project:
                    project_name = project['name']

            cursor = conn.execute("""
                INSERT INTO tasks (
                    title, description, project, executor_id, author_id,
                    deadline, status, task_type, task_format, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data.get('title'),
                task_data.get('description'),
                project_name,
                task_data.get('executor_id'),
                creator['id'],
                task_data.get('deadline'),
                'new',  # статус по умолчанию
                self.get_task_type_for_webapp(task_data.get('task_type')),
                task_data.get('format'),
                datetime.now()  # Используем локальное время
            ))

            task_id = cursor.lastrowid
            conn.commit()

            # Получаем telegram_id исполнителя для отправки уведомления
            executor = conn.execute(
                "SELECT telegram_id FROM users WHERE id = ?",
                (task_data.get('executor_id'),)
            ).fetchone()

            conn.close()

            # Отправляем уведомление исполнителю в фоновом режиме (не блокируя ответ)
            if executor and executor['telegram_id']:
                logger.info(f"📨 Отправка уведомления о задаче #{task_id} исполнителю {executor['name']} (telegram_id: {executor['telegram_id']})")
                asyncio.create_task(
                    self.send_task_notification(
                        executor_telegram_id=executor['telegram_id'],
                        task_id=task_id,
                        task_data=task_data
                    )
                )
            else:
                logger.warning(f"⚠️ Уведомление не отправлено: executor={executor}, telegram_id={executor.get('telegram_id') if executor else 'None'}")

            # Формируем сообщение об успехе
            success_message = f"""
✅ **Задача успешно создана!**

📋 **Задача #{task_id}**
┌─────────────────────────────────┐
│ 📝 **Название:** {task_data.get('title')}
│ 👤 **Исполнитель:** {task_data.get('executor_name')}
│ 📁 **Проект:** {task_data.get('project_name')}
│ 🏷️ **Тип:** {self.get_task_type_name(task_data.get('task_type', ''))}
"""

            if task_data.get('format'):
                success_message += f"│ 📐 **Формат:** {task_data.get('format')}\n"

            success_message += f"│ ⏰ **Дедлайн:** {task_data.get('deadline_text', 'Не установлен')}\n"
            success_message += "└─────────────────────────────────┘\n\n"
            success_message += "📲 **Задача отображается в системе и доступна исполнителю.**"

            # Очищаем историю чата
            await self.bot.clear_chat_history(update, context, limit=50)

            # Создаем главное меню
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            await update.message.reply_text(
                success_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # Очищаем данные создания задачи
            context.user_data.pop('admin_task_creation', None)

        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            await update.message.reply_text(
                "❌ **Произошла ошибка при создании задачи**\n\n"
                "Попробуйте еще раз или обратитесь к администратору.",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )

    async def handle_edit_task(self, update, context):
        """Обработка редактирования задачи - показ меню выбора шага"""
        task_data = context.user_data.get('admin_task_creation', {})

        # Сохраняем текущее состояние перед редактированием
        task_data['editing'] = True
        task_data['step'] = 'edit_selection'
        context.user_data['admin_task_creation'] = task_data

        # Создаем кнопки для всех шагов, которые можно редактировать
        keyboard = []

        # Роль исполнителя
        executor_role = task_data.get('executor_role', 'не выбрана')
        role_display = {
            'admin': 'Администратор',
            'designer': 'Дизайнер',
            'smm_manager': 'СММ-менеджер'
        }.get(executor_role, executor_role)
        keyboard.append([f"👤 Роль: {role_display}"])

        # Исполнитель
        executor_name = task_data.get('executor_name', 'не выбран')
        keyboard.append([f"👷 Исполнитель: {executor_name}"])

        # Проект
        project_name = task_data.get('project_name', 'не выбран')
        keyboard.append([f"📁 Проект: {project_name}"])

        # Тип задачи
        task_type = task_data.get('task_type', 'не выбран')
        keyboard.append([f"🏷️ Тип задачи: {task_type}"])

        # Формат (для дизайнеров)
        if executor_role == 'designer' and task_data.get('format'):
            format_val = task_data.get('format', 'не выбран')
            keyboard.append([f"📐 Формат: {format_val}"])

        # Название задачи
        title = task_data.get('title', 'не указано')
        # Обрезаем название если оно слишком длинное
        if len(title) > 30:
            title = title[:30] + "..."
        keyboard.append([f"📝 Название: {title}"])

        # Описание
        description = task_data.get('description', '')
        if description:
            desc_preview = description[:30] + "..." if len(description) > 30 else description
            keyboard.append([f"📋 Описание: {desc_preview}"])
        else:
            keyboard.append([f"📋 Описание: не добавлено"])

        # Дедлайн
        deadline = task_data.get('deadline_display', 'не установлен')
        keyboard.append([f"⏰ Дедлайн: {deadline}"])

        # Кнопка возврата к предпросмотру
        keyboard.append(["🔙 Вернуться к просмотру"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "✏️ **Редактирование задачи**\n\n"
            "Выберите шаг, который хотите отредактировать:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    async def check_and_return_to_preview(self, update, context):
        """Проверяет флаг возврата к предпросмотру и возвращает если нужно"""
        task_data = context.user_data.get('admin_task_creation', {})
        if task_data.get('return_to_preview'):
            task_data['step'] = 'final_confirmation'
            task_data.pop('return_to_preview', None)
            context.user_data['admin_task_creation'] = task_data
            await self.show_task_preview(update, context)
            return True
        return False

    async def get_users_by_role(self, role: str) -> List[Dict]:
        """Получение пользователей по роли из базы данных"""
        conn = self.bot.get_db_connection()
        if not conn:
            return []

        try:
            cursor = self._execute_query(conn, """
                SELECT id, name, telegram_username, role
                FROM users
                WHERE role = ? AND is_active = 1
                ORDER BY name
            """, (role,))

            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'name': row[1],
                    'telegram_username': row[2],
                    'role': row[3]
                })

            conn.close()
            return users
        except Exception as e:
            logger.error(f"Ошибка получения пользователей по роли {role}: {e}")
            if conn:
                conn.close()
            return []

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        conn = self.bot.get_db_connection()
        if not conn:
            return None

        try:
            cursor = self._execute_query(conn, """
                SELECT id, name, telegram_username, role
                FROM users
                WHERE id = ?
            """, (user_id,))

            user = cursor.fetchone()
            conn.close()

            if user:
                return {
                    'id': user[0],
                    'name': user[1],
                    'telegram_username': user[2],
                    'role': user[3]
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            conn.close()
            return None

    async def get_all_projects(self) -> List[Dict]:
        """Получение всех проектов из базы данных"""
        conn = self.bot.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute("""
                SELECT id, name, start_date
                FROM projects
                WHERE is_archived = 0
                ORDER BY start_date DESC
            """)

            projects = []
            for row in cursor.fetchall():
                projects.append({
                    'id': row[0],
                    'name': row[1],
                    'start_date': row[2] if len(row) > 2 else None
                })

            conn.close()
            return projects
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
            if conn:
                conn.close()
            return []

    async def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Получение проекта по ID"""
        conn = self.bot.get_db_connection()
        if not conn:
            return None

        try:
            cursor = conn.execute("""
                SELECT id, name
                FROM projects
                WHERE id = ?
            """, (project_id,))
            project = cursor.fetchone()
            conn.close()
            return dict(project) if project else None
        except Exception as e:
            logger.error(f"Ошибка получения проекта: {e}")
            conn.close()
            return None

    def get_role_name(self, role: str) -> str:
        """Получение русского названия роли"""
        role_names = {
            'admin': '🔑 Администратор',
            'smm_manager': '📱 СММ-менеджер',
            'designer': '🎨 Дизайнер'
        }
        return role_names.get(role, role)

    async def get_task_types_by_role(self, role: str) -> List[str]:
        """Получение типов задач в зависимости от роли из API"""
        try:
            # Пробуем получить из API
            task_types_data = await self.bot.get_task_types_from_api(role)
            if task_types_data:
                logger.info(f"✅ Получены типы задач из API для роли {role}")
                return [display_name for display_name, internal_name in task_types_data]
            else:
                logger.warning(f"API вернул пустой результат, используем fallback для роли {role}")
                return self.get_fallback_task_types_by_role(role)
        except Exception as e:
            logger.error(f"Ошибка API запроса типов задач: {e}, используем fallback")
            return self.get_fallback_task_types_by_role(role)

    def get_fallback_task_types_by_role(self, role: str) -> List[str]:
        """Fallback статические типы задач в зависимости от роли (соответствуют API)"""
        task_types = {
            'designer': [
                "🎞️ Motion",
                "🖼️ Статика",
                "🎬 Видео",
                "🖼️ Карусель",
                "📌 Другое"
            ],
            'smm_manager': [
                "[INFO] Публикация",
                "[INFO] Контент план",
                "📊 Отчет",
                "📹 Съемка",
                "🤝 Встреча",
                "📈 Стратегия",
                "🎤 Презентация",
                "🗂️ Админ задачи",
                "🔎 Анализ",
                "[DB] Брифинг",
                "📜 Сценарий",
                "📌 Другое"
            ],
            'admin': [
                "📝 Публикация",
                "📸 Съемки",
                "📈 Стратегия",
                "📊 Отчет",
                "💰 Бухгалтерия",
                "🤝 Встреча",
                "📄 Документы",
                "👥 Работа с кадрами",
                "📋 Планерка",
                "⚙️ Администраторские задачи",
                "🎤 Собеседование",
                "📜 Договор",
                "🔄 Другое"
            ]
        }
        return task_types.get(role, [])

    def get_formats_for_designer(self) -> List[tuple]:
        """Получение форматов для дизайнера"""
        return [
            ("📱 9:16", "9:16"),
            ("⬜ 1:1", "1:1"),
            ("📐 4:5", "4:5"),
            ("📺 16:9", "16:9"),
            ("🔄 Другое", "other")
        ]

    def get_task_type_name(self, task_type: str) -> str:
        """Получение читаемого названия типа задачи"""
        type_names = {
            'motion': '🎬 Motion',
            'static': '🖼️ Статика',
            'video': '📹 Видео',
            'carousel': '🎠 Карусель',
            'publication': '📝 Публикация',
            'content_plan': '📅 Контент план',
            'report': '📊 Отчет',
            'shooting': '📸 Съемка',
            'meeting': '🤝 Встреча',
            'strategy': '📈 Стратегия',
            'presentation': '📋 Презентация',
            'admin_tasks': '⚙️ Админ задачи',
            'analysis': '🔍 Анализ',
            'briefing': '📑 Брифинг',
            'script': '📝 Сценарий',
            'accounting': '💰 Бухгалтерия',
            'documents': '📄 Документы',
            'hr': '👥 Работа с кадрами',
            'planning': '📋 Планерка',
            'interview': '🎤 Собеседование',
            'contract': '📜 Договор',
            'other': '🔄 Другое'
        }
        return type_names.get(task_type, task_type)

    def get_task_type_for_webapp(self, task_type: str) -> str:
        """Преобразование типа задачи в формат для веб-приложения"""
        # Маппинг внутренних ключей к названиям, которые ожидает веб-приложение
        webapp_mapping = {
            'motion': 'Motion',
            'static': 'Статика',
            'video': 'Видео',
            'carousel': 'Карусель',
            'publication': 'Публикация',
            'content_plan': 'Контент план',
            'report': 'Отчет',
            'shooting': 'Съемка',
            'meeting': 'Встреча',
            'strategy': 'Стратегия',
            'presentation': 'Презентация',
            'admin_tasks': 'Администраторские задачи',
            'analysis': 'Анализ',
            'briefing': 'Брифинг',
            'script': 'Сценарий',
            'accounting': 'Бухгалтерия',
            'documents': 'Документы',
            'hr': 'Работа с кадрами',
            'planning': 'Планерка',
            'interview': 'Собеседование',
            'contract': 'Договор',
            'other': 'Другое'
        }
        return webapp_mapping.get(task_type, task_type)

    # ================== МЕТОДЫ ДЛЯ ПРОСМОТРА АКТИВНЫХ ЗАДАЧ ==================

    async def handle_active_tasks_start(self, update, context):
        """Начало просмотра активных задач - выбор роли"""
        # Инициализируем просмотр активных задач
        context.user_data['active_tasks_view'] = {
            'step': 'role_selection'
        }

        # Создаем клавиатуру с основными ролями из приложения
        keyboard = [
            ["🔑 Администратор", "📱 СММ-менеджер"],
            ["🎨 Дизайнер", "📋 Все активные задачи"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📋 **Просмотр активных задач**\n\n"
            "👥 Выберите роль для просмотра активных задач:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_active_tasks_role_selection(self, update, context, role_text):
        """Обработка выбора роли для просмотра активных задач"""
        # Маппинг текста на роль
        role_mapping = {
            "🔑 Администратор": "admin",
            "📱 СММ-менеджер": "smm_manager",
            "🎨 Дизайнер": "designer",
            "👑 Главный СММ": "head_smm"
        }

        if role_text == "📋 Все активные задачи":
            # Показываем все активные задачи
            await self.show_all_active_tasks(update, context)
            return

        role = role_mapping.get(role_text)
        if not role:
            await update.message.reply_text(
                "❌ Неизвестная роль. Попробуйте еще раз.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Обновляем данные просмотра
        view_data = context.user_data.get('active_tasks_view', {})
        view_data['role'] = role
        view_data['step'] = 'user_selection'
        context.user_data['active_tasks_view'] = view_data

        # Получаем пользователей этой роли
        users = await self.get_users_by_role_for_active_tasks(role)

        if not users:
            await update.message.reply_text(
                f"🔍 Нет пользователей с ролью **{self.get_role_display_name(role)}**\n\n"
                f"Возможные причины:\n"
                f"• Нет активных пользователей с этой ролью\n"
                f"• Все пользователи этой роли неактивны",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            # Очищаем данные просмотра
            context.user_data.pop('active_tasks_view', None)
            return

        # Создаем клавиатуру с пользователями (по 3 в ряд)
        keyboard = []
        user_buttons = [f"👤 {user['name']}" for user in users]
        for i in range(0, len(user_buttons), 3):
            row = user_buttons[i:i+3]
            keyboard.append(row)

        keyboard.append(["🔙 Назад к выбору роли"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"👥 **Роль: {self.get_role_display_name(role)}**\n\n"
            f"Выберите сотрудника для просмотра активных задач:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_active_tasks_user_selection(self, update, context, user_text):
        """Обработка выбора пользователя для просмотра активных задач"""
        view_data = context.user_data.get('active_tasks_view', {})
        role = view_data.get('role')

        if not role:
            await update.message.reply_text(
                "❌ Ошибка: роль не выбрана",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Извлекаем имя пользователя из текста (убираем "👤 ")
        user_name = user_text.replace("👤 ", "")

        # Получаем пользователей этой роли
        users = await self.get_users_by_role_for_active_tasks(role)
        user = None
        for u in users:
            if u['name'] == user_name:
                user = u
                break

        if not user:
            await update.message.reply_text(
                f"❌ Пользователь **{user_name}** не найден",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Показываем активные задачи пользователя
        await self.show_user_active_tasks(update, context, user)

    async def show_user_active_tasks(self, update, context, user):
        """Показать активные задачи конкретного пользователя"""
        try:
            # Получаем подключение к БД
            conn = self.bot.get_db_connection()
            if not conn:
                await update.message.reply_text(
                    "❌ Ошибка подключения к базе данных",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Получаем активные задачи пользователя (статусы "new", "in_progress" и "overdue")
            cursor = conn.execute("""
                SELECT id, title, description, project, task_type, deadline, created_at
                FROM tasks
                WHERE executor_id = ? AND status IN ('new', 'in_progress', 'overdue')
                ORDER BY created_at DESC
            """, (user['id'],))

            tasks = cursor.fetchall()

            if not tasks:
                # Получаем роль текущего пользователя для определения кнопок
                current_user = update.effective_user
                current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

                # Создаем кнопки главного меню в зависимости от роли
                if current_db_user and current_db_user['role'] == 'admin':
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                else:
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    f"📭 **{user['name']}** не имеет активных задач\n\n"
                    f"Все задачи выполнены или завершены! ✅\n\n"
                    f"🏠 Выберите следующее действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                # Очищаем данные просмотра
                context.user_data.pop('active_tasks_view', None)
                return

            # Отправляем каждую задачу отдельным сообщением
            for i, task in enumerate(tasks, 1):
                task_info = []

                # Заголовок задачи с номером
                task_info.append(f"📝 **Задача #{i}**")
                task_info.append(f"**{task[1]}**")  # title
                task_info.append("─────────────────────")

                # Проект
                if task[3]:  # project
                    task_info.append(f"🎯 **Проект:** {task[3]}")

                # Тип задачи
                if task[4]:  # task_type
                    task_info.append(f"📂 **Тип:** {self.get_task_type_for_webapp(task[4])}")

                # Дедлайн
                if task[5]:  # deadline
                    try:
                        from datetime import datetime
                        # Дедлайн уже в локальном времени
                        deadline_dt = datetime.fromisoformat(task[5].replace('Z', '+00:00'))
                        deadline_str = deadline_dt.strftime("%d.%m.%Y в %H:%M")
                        task_info.append(f"⏰ **Дедлайн:** {deadline_str}")

                        # Статус всегда "В работе" для активных задач
                        task_info.append("🟢 **Статус:** В работе")

                        # Проверяем, сколько времени осталось до дедлайна
                        now = datetime.now()
                        time_left = local_deadline - now
                        if time_left.days < 0:
                            task_info.append("🔴 **Срок:** Просрочен!")
                        elif time_left.days == 0:
                            task_info.append("🟡 **Срок:** Сегодня!")
                        elif time_left.days == 1:
                            task_info.append("🟠 **Срок:** Завтра")
                        else:
                            task_info.append(f"⏱️ **Осталось:** {time_left.days} дн.")
                    except:
                        task_info.append(f"⏰ **Дедлайн:** {task[5]}")

                # Описание
                if task[2]:  # description
                    desc = task[2]
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    task_info.append(f"📄 **Описание:**\n{desc}")

                # Дата создания
                if task[6]:  # created_at
                    try:
                        from datetime import datetime
                        created_dt = datetime.fromisoformat(task[6].replace('Z', '+00:00'))
                        created_str = created_dt.strftime("%d.%m.%Y")
                        task_info.append(f"📅 **Создано:** {created_str}")
                    except:
                        pass

                task_message = "\n".join(task_info)

                # Проверяем, последняя ли это задача
                is_last_task = (i == len(tasks))

                if is_last_task:
                    # Для последней задачи добавляем inline кнопки и затем отдельное сообщение с меню
                    # Создаем inline кнопки для задачи
                    inline_keyboard = [
                        [
                            InlineKeyboardButton("✅ Завершить", callback_data=f"complete_task_{task[0]}"),
                            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_task_{task[0]}")
                        ]
                    ]
                    inline_markup = InlineKeyboardMarkup(inline_keyboard)

                    # Отправляем задачу с inline кнопками
                    await update.message.reply_text(
                        task_message,
                        parse_mode='Markdown',
                        reply_markup=inline_markup
                    )

                    # Добавляем небольшое информационное сообщение с обычной клавиатурой
                    # Получаем роль текущего пользователя для определения кнопок
                    current_user = update.effective_user
                    current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

                    # Создаем кнопки главного меню в зависимости от роли
                    if current_db_user and current_db_user['role'] == 'admin':
                        keyboard = [
                            ["🔧 Управление задачами"],
                            ["💰 Расходы"]
                        ]
                    else:
                        keyboard = [
                            ["🔧 Управление задачами"],
                            ["💰 Расходы"]
                        ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                    # Отправляем сводное сообщение
                    summary_text = (
                        f"📋 **Активные задачи: {user['name']}**\n"
                        f"👥 **Роль:** {self.get_role_display_name(user.get('role', 'unknown'))}\n"
                        f"📊 **Всего активных задач:** {len(tasks)}"
                    )

                    await update.message.reply_text(
                        summary_text,
                        parse_mode='Markdown'
                    )

                    # Отправляем информационное сообщение с клавиатурой
                    await update.message.reply_text(
                        "📌 Выберите действие:",
                        reply_markup=reply_markup
                    )
                else:
                    # Для остальных задач только inline кнопки
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Завершить", callback_data=f"complete_task_{task[0]}"),
                            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_task_{task[0]}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await update.message.reply_text(
                        task_message,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )

                    # Небольшая задержка между задачами
                    await asyncio.sleep(0.3)

            # Клавиатура уже добавлена к последней задаче, ничего больше делать не нужно

        except Exception as e:
            print(f"Ошибка при получении активных задач: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении списка задач",
                reply_markup=ReplyKeyboardRemove()
            )
        finally:
            # Очищаем данные просмотра
            context.user_data.pop('active_tasks_view', None)

    async def show_all_active_tasks(self, update, context):
        """Показать все активные задачи во всей системе"""
        try:
            # Получаем подключение к БД
            conn = self.bot.get_db_connection()
            if not conn:
                await update.message.reply_text(
                    "❌ Ошибка подключения к базе данных",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            # Получаем все активные задачи (только статус в работе) с информацией об исполнителях
            cursor = conn.execute("""
                SELECT t.id, t.title, t.project, t.task_type, t.deadline, u.name as executor_name, u.role
                FROM tasks t
                LEFT JOIN users u ON t.executor_id = u.id
                WHERE t.status = 'in_progress'
                ORDER BY t.created_at DESC
            """)

            tasks = cursor.fetchall()

            if not tasks:
                # Получаем роль текущего пользователя для определения кнопок
                current_user = update.effective_user
                current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

                # Создаем кнопки главного меню в зависимости от роли
                if current_db_user and current_db_user['role'] == 'admin':
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                else:
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    f"📭 **Нет активных задач в системе**\n\n"
                    f"Все задачи выполнены! ✅\n\n"
                    f"🏠 Выберите следующее действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                # Очищаем данные просмотра
                context.user_data.pop('active_tasks_view', None)
                return

            # Группируем задачи по исполнителям
            tasks_by_user = {}
            for task in tasks:
                executor = task[5] or "Не назначен"
                role = task[6] or "unknown"

                if executor not in tasks_by_user:
                    tasks_by_user[executor] = {
                        'role': role,
                        'tasks': []
                    }
                tasks_by_user[executor]['tasks'].append(task)

            # Отправляем сводное сообщение
            total_users = len(tasks_by_user)
            summary_text = (
                f"📋 **Все активные задачи в системе**\n"
                f"📊 **Всего активных задач:** {len(tasks)}\n"
                f"👥 **Сотрудников с задачами:** {total_users}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            await update.message.reply_text(
                summary_text,
                parse_mode='Markdown'
            )

            await asyncio.sleep(0.5)

            # Отправляем задачи каждого пользователя отдельными сообщениями
            user_count = 0
            for executor, data in tasks_by_user.items():
                user_count += 1
                role_display = self.get_role_display_name(data['role'])

                user_header = (
                    f"👤 **{executor}**\n"
                    f"🎭 **Роль:** {role_display}\n"
                    f"📝 **Активных задач:** {len(data['tasks'])}\n"
                    f"─────────────────────"
                )

                await update.message.reply_text(
                    user_header,
                    parse_mode='Markdown'
                )

                await asyncio.sleep(0.3)

                # Отправляем каждую задачу пользователя
                for i, task in enumerate(data['tasks'], 1):
                    task_info = []
                    task_info.append(f"📌 **Задача #{i} для {executor}**")
                    task_info.append(f"**{task[1]}**")  # title
                    task_info.append("─────────────────────")

                    if task[2]:  # project
                        task_info.append(f"🎯 **Проект:** {task[2]}")

                    if task[3]:  # task_type
                        task_info.append(f"📂 **Тип:** {self.get_task_type_for_webapp(task[3])}")

                    if task[4]:  # deadline
                        try:
                            # Дедлайн уже в локальном времени
                            deadline_dt = datetime.fromisoformat(task[4].replace('Z', '+00:00'))
                            deadline_str = deadline_dt.strftime("%d.%m.%Y в %H:%M")
                            task_info.append(f"⏰ **Дедлайн:** {deadline_str}")

                            # Статус всегда "В работе" для активных задач
                            task_info.append("🟢 **Статус:** В работе")

                            # Проверяем срочность дедлайна
                            now = datetime.now()
                            time_left = local_deadline - now
                            if time_left.days < 0:
                                task_info.append("🔴 **Срок:** Просрочен!")
                            elif time_left.days == 0:
                                task_info.append("🟡 **Срок:** Сегодня!")
                            elif time_left.days == 1:
                                task_info.append("🟠 **Срок:** Завтра")
                            else:
                                task_info.append(f"⏱️ **Осталось:** {time_left.days} дн.")
                        except:
                            task_info.append(f"⏰ **Дедлайн:** {task[4]}")

                    task_message = "\n".join(task_info)

                    # Создаем inline кнопки для каждой задачи
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Завершить", callback_data=f"complete_task_{task[0]}"),
                            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_task_{task[0]}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await update.message.reply_text(
                        task_message,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )

                    if i < len(data['tasks']):
                        await asyncio.sleep(0.2)

                # Небольшая пауза между пользователями
                if user_count < total_users:
                    await asyncio.sleep(0.5)

            # Финальное сообщение с кнопками главного меню
            await asyncio.sleep(0.5)

            # Получаем роль текущего пользователя для определения кнопок
            current_user = update.effective_user
            current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

            # Создаем кнопки главного меню в зависимости от роли
            if current_db_user and current_db_user['role'] == 'admin':
                keyboard = [
                    ["🔧 Управление задачами"],
                    ["💰 Расходы"]
                ]
            else:
                keyboard = [
                    ["🔧 Управление задачами"],
                    ["💰 Расходы"]
                ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            await update.message.reply_text(
                f"✅ **Обзор завершен**\n"
                f"📊 Показано {len(tasks)} задач от {total_users} сотрудников\n"
                f"💼 Все задачи в статусе: В работе\n\n"
                f"🏠 Выберите следующее действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"Ошибка при получении всех активных задач: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении списка задач",
                reply_markup=ReplyKeyboardRemove()
            )
        finally:
            # Очищаем данные просмотра
            context.user_data.pop('active_tasks_view', None)

    async def get_users_by_role_for_active_tasks(self, role_key):
        """Получить пользователей по роли для просмотра активных задач"""
        try:
            conn = self.bot.get_db_connection()
            if not conn:
                return []

            cursor = conn.execute("""
                SELECT id, name, telegram_username, role
                FROM users
                WHERE role = ? AND is_active = 1
                ORDER BY name
            """, (role_key,))

            users = []
            rows = cursor.fetchall()
            for row in rows:
                users.append({
                    'id': row[0],
                    'name': row[1],
                    'telegram_username': row[2],
                    'role': row[3]
                })

            return users

        except Exception as e:
            print(f"Ошибка при получении пользователей по роли {role_key}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_role_display_name(self, role):
        """Получить отображаемое имя роли"""
        role_names = {
            'admin': 'Администратор',
            'smm_manager': 'СММ-менеджер',
            'designer': 'Дизайнер',
            'head_smm': 'Главный СММ'
        }
        return role_names.get(role, role)

    # ================== МЕТОДЫ ДЛЯ ПРОСМОТРА АРХИВНЫХ ЗАДАЧ ==================

    async def handle_archived_tasks_start(self, update, context):
        """Начало просмотра архивных задач - выбор роли"""
        # Инициализируем просмотр архивных задач
        context.user_data['archived_tasks_view'] = {
            'step': 'role_selection'
        }

        # Создаем клавиатуру с основными ролями из приложения
        keyboard = [
            ["🔑 Администратор", "📱 СММ-менеджер"],
            ["🎨 Дизайнер"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📁 **Просмотр архивных задач**\n\n"
            "👥 Выберите роль для просмотра завершенных задач:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_archived_tasks_role_selection(self, update, context, role_text):
        """Обработка выбора роли для просмотра архивных задач"""
        # Маппинг текста на роль
        role_mapping = {
            "🔑 Администратор": "admin",
            "📱 СММ-менеджер": "smm_manager",
            "🎨 Дизайнер": "designer"
        }

        role = role_mapping.get(role_text)
        if not role:
            return

        # Сохраняем выбранную роль
        archived_data = context.user_data.get('archived_tasks_view', {})
        archived_data['role'] = role
        archived_data['step'] = 'user_selection'
        context.user_data['archived_tasks_view'] = archived_data

        # Получаем пользователей выбранной роли
        users = await self.get_users_by_role_for_active_tasks(role)

        if not users:
            await update.message.reply_text(
                f"❌ Нет пользователей с ролью {role_text}",
                parse_mode='Markdown'
            )
            return

        # Создаем кнопки с пользователями (по 2 в ряд)
        keyboard = []
        user_buttons = [f"👤 {user['name']}" for user in users]
        for i in range(0, len(user_buttons), 2):
            row = user_buttons[i:i+2]
            keyboard.append(row)

        keyboard.append(["🔙 Назад к выбору роли"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"Выберите сотрудника для просмотра завершенных задач:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_archived_tasks_user_selection(self, update, context, user_text):
        """Обработка выбора пользователя для просмотра архивных задач"""
        # Убираем эмодзи из текста
        user_name = user_text.replace("👤 ", "").strip()

        # Получаем роль из данных контекста
        archived_data = context.user_data.get('archived_tasks_view', {})
        selected_role = archived_data.get('role')

        if not selected_role:
            await update.message.reply_text("❌ Ошибка: роль не выбрана")
            return

        # Получаем пользователей этой роли
        users = await self.get_users_by_role_for_active_tasks(selected_role)

        # Ищем пользователя по имени
        user = None
        for u in users:
            if u['name'] == user_name:
                user = u
                break

        if not user:
            await update.message.reply_text(f"❌ Пользователь {user_name} не найден")
            return

        # Сохраняем выбранного пользователя и переходим к выбору периода
        archived_data['user_id'] = user['id']
        archived_data['user_name'] = user['name']
        archived_data['step'] = 'period_selection'
        context.user_data['archived_tasks_view'] = archived_data

        # Создаем кнопки выбора периода
        keyboard = [
            ["📅 За сегодня", "📅 За неделю"],
            ["📅 За месяц", "📅 За все время"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"👤 **Сотрудник:** {user['name']}\n\n"
            f"📅 **Выберите период для просмотра завершенных задач:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_archived_tasks_period_selection(self, update, context, period_text):
        """Обработка выбора периода для просмотра архивных задач"""

        archived_data = context.user_data.get('archived_tasks_view', {})
        user_id = archived_data.get('user_id')
        user_name = archived_data.get('user_name')

        if not user_id:
            await update.message.reply_text("❌ Ошибка: пользователь не выбран")
            return

        # Создаем объект пользователя
        user = {
            'id': user_id,
            'name': user_name,
            'role': archived_data.get('role')
        }

        # Сохраняем период
        archived_data['period'] = period_text
        context.user_data['archived_tasks_view'] = archived_data

        # Показываем завершенные задачи пользователя с учетом периода
        await self.show_user_archived_tasks(update, context, user, period_text)

    async def show_user_archived_tasks(self, update, context, user, period_text):
        """Показать завершенные задачи пользователя за выбранный период"""
        try:
            conn = self.bot.get_db_connection()
            if not conn:
                await update.message.reply_text("❌ Ошибка подключения к базе данных")
                return

            # Вычисляем дату начала периода
            from datetime import datetime, timedelta
            now = datetime.now()

            if period_text == "📅 За сегодня":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_label = "сегодня"
            elif period_text == "📅 За неделю":
                start_date = now - timedelta(days=7)
                period_label = "за последнюю неделю"
            elif period_text == "📅 За месяц":
                start_date = now - timedelta(days=30)
                period_label = "за последний месяц"
            else:  # За все время
                start_date = None
                period_label = "за все время"

            # Получаем завершенные задачи пользователя (только статус "done")
            if start_date:
                cursor = conn.execute("""
                    SELECT id, title, description, project, task_type, deadline, created_at, finished_at
                    FROM tasks
                    WHERE executor_id = ? AND status = 'done' AND finished_at >= ?
                    ORDER BY finished_at DESC
                    LIMIT 50
                """, (user['id'], start_date.isoformat()))
            else:
                cursor = conn.execute("""
                    SELECT id, title, description, project, task_type, deadline, created_at, finished_at
                    FROM tasks
                    WHERE executor_id = ? AND status = 'done'
                    ORDER BY finished_at DESC
                    LIMIT 50
                """, (user['id'],))

            tasks = cursor.fetchall()

            if not tasks:
                # Получаем роль текущего пользователя для определения кнопок
                current_user = update.effective_user
                current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

                # Создаем кнопки главного меню в зависимости от роли
                if current_db_user and current_db_user['role'] == 'admin':
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                else:
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"]
                    ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    f"📭 **{user['name']}** не имеет завершенных задач\n\n"
                    f"🏠 Выберите следующее действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                # Очищаем данные просмотра
                context.user_data.pop('archived_tasks_view', None)
                return

            # Отправляем каждую задачу отдельным сообщением
            for i, task in enumerate(tasks, 1):
                task_info = []

                # Заголовок задачи с номером
                task_info.append(f"📝 **Задача #{i}**")
                task_info.append(f"**{task[1]}**")  # title
                task_info.append("─────────────────────")

                # Проект
                if task[3]:  # project
                    task_info.append(f"🎯 **Проект:** {task[3]}")

                # Тип задачи
                if task[4]:  # task_type
                    task_info.append(f"📂 **Тип:** {self.get_task_type_for_webapp(task[4])}")

                # Дедлайн
                if task[5]:  # deadline
                    try:
                        from datetime import datetime
                        deadline_dt = datetime.fromisoformat(task[5].replace('Z', '+00:00'))
                        deadline_str = deadline_dt.strftime("%d.%m.%Y в %H:%M")
                        task_info.append(f"⏰ **Дедлайн:** {deadline_str}")
                    except:
                        task_info.append(f"⏰ **Дедлайн:** {task[5]}")

                # Статус завершено
                task_info.append("✅ **Статус:** Завершено")

                # Дата завершения
                if task[7]:  # finished_at
                    try:
                        from datetime import datetime
                        finished_dt = datetime.fromisoformat(task[7].replace('Z', '+00:00'))
                        finished_str = finished_dt.strftime("%d.%m.%Y в %H:%M")
                        task_info.append(f"🏁 **Завершено:** {finished_str}")
                    except:
                        pass

                # Описание
                if task[2]:  # description
                    desc = task[2]
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    task_info.append(f"📄 **Описание:**\n{desc}")

                # Дата создания
                if task[6]:  # created_at
                    try:
                        from datetime import datetime
                        created_dt = datetime.fromisoformat(task[6].replace('Z', '+00:00'))
                        created_str = created_dt.strftime("%d.%m.%Y")
                        task_info.append(f"📅 **Создано:** {created_str}")
                    except:
                        pass

                task_message = "\n".join(task_info)

                # Проверяем, последняя ли это задача
                is_last_task = (i == len(tasks))

                if is_last_task:
                    # Для последней задачи добавляем сообщение с клавиатурой
                    # Убираем Markdown чтобы избежать ошибок парсинга
                    await update.message.reply_text(
                        task_message
                    )

                    # Получаем роль текущего пользователя для определения кнопок
                    current_user = update.effective_user
                    current_db_user = self.bot.get_user_by_telegram_id(current_user.id, current_user.username)

                    # Создаем кнопки главного меню в зависимости от роли
                    if current_db_user and current_db_user['role'] == 'admin':
                        keyboard = [
                            ["🔧 Управление задачами"],
                            ["💰 Расходы"]
                        ]
                    else:
                        keyboard = [
                            ["🔧 Управление задачами"],
                            ["💰 Расходы"]
                        ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                    # Отправляем сводное сообщение
                    summary_text = (
                        f"📁 **Завершенные задачи: {user['name']}**\n"
                        f"👥 **Роль:** {self.get_role_display_name(user.get('role', 'unknown'))}\n"
                        f"📅 **Период:** {period_label}\n"
                        f"📊 **Всего завершенных задач:** {len(tasks)}"
                    )

                    await update.message.reply_text(
                        summary_text,
                        parse_mode='Markdown'
                    )

                    # Отправляем информационное сообщение с клавиатурой
                    await update.message.reply_text(
                        "📌 Выберите действие:",
                        reply_markup=reply_markup
                    )
                else:
                    # Для остальных задач только сообщение
                    await update.message.reply_text(
                        task_message
                    )

                    # Небольшая задержка между задачами
                    await asyncio.sleep(0.3)

        except Exception as e:
            print(f"Ошибка при получении завершенных задач: {e}")
            await update.message.reply_text(
                f"❌ Произошла ошибка при загрузке завершенных задач: {str(e)}",
                parse_mode='Markdown'
            )
        finally:
            if conn:
                conn.close()

    async def handle_admin_message(self, update, context, text):
        """Централизованная обработка администраторских сообщений"""

        # Обработка workflow активных задач
        active_tasks_data = context.user_data.get('active_tasks_view')
        # Обработка workflow архивных задач
        archived_tasks_data = context.user_data.get('archived_tasks_view')

        # Дебаг всех данных пользователя

        # Дополнительная отладка для понимания проблемы
        if text in ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер"]:
            logger.debug(f"Role button pressed: {text}, active={active_tasks_data is not None}, archived={archived_tasks_data is not None}")

        # Начало просмотра активных задач
        if text == "📋 Активные задачи":
            await self.handle_active_tasks_start(update, context)
            return True

        # Начало просмотра архивных задач
        elif text == "📁 Архив задач":
            await self.handle_archived_tasks_start(update, context)
            return True

        # Начало просмотра непринятых задач
        elif text == "🆕 Не принятые в работу":
            await self.handle_new_tasks_start(update, context)
            return True

        # Обработка выбора роли - сначала проверяем архивные, потом активные
        if text in ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер"]:

            # Проверяем архивные задачи
            if archived_tasks_data and archived_tasks_data.get('step') == 'role_selection':
                try:
                    await self.handle_archived_tasks_role_selection(update, context, text)
                    return True
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return True
            # Проверяем активные задачи
            elif active_tasks_data and active_tasks_data.get('step') == 'role_selection':
                try:
                    await self.handle_active_tasks_role_selection(update, context, text)
                    return True
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return True
            else:
                logger.debug("No matching workflow for role button")

        # Обработка специальных кнопок активных задач
        if active_tasks_data and active_tasks_data.get('step') == 'role_selection':
            if text == "📋 Все активные задачи":
                await self.show_all_active_tasks(update, context)
                return True

        # Обработка выбора исполнителя в активных задачах
        elif active_tasks_data and active_tasks_data.get('step') == 'user_selection':
            if text == "🔙 Назад к выбору роли":
                # Возвращаемся к выбору роли
                await self.handle_active_tasks_start(update, context)
                return True

            selected_role = active_tasks_data.get('role')
            if selected_role:
                users = await self.get_users_by_role_for_active_tasks(selected_role)
                for user in users:
                    # Сравниваем с форматом кнопки
                    button_text = f"👤 {user['name']}"
                    if button_text == text:
                        await self.handle_active_tasks_user_selection(update, context, text)
                        return True

        # Обработка выбора исполнителя в архивных задачах
        elif archived_tasks_data and archived_tasks_data.get('step') == 'user_selection':
            if text == "🔙 Назад к выбору роли":
                # Возвращаемся к выбору роли
                await self.handle_archived_tasks_start(update, context)
                return True

            selected_role = archived_tasks_data.get('role')
            if selected_role:
                users = await self.get_users_by_role_for_active_tasks(selected_role)
                for user in users:
                    # Сравниваем с форматом кнопки
                    button_text = f"👤 {user['name']}"
                    if button_text == text:
                        await self.handle_archived_tasks_user_selection(update, context, text)
                        return True

        # Обработка выбора периода в архивных задачах
        elif archived_tasks_data and archived_tasks_data.get('step') == 'period_selection':
            if text == "🔙 Назад":
                # Возвращаемся к выбору пользователя
                selected_role = archived_tasks_data.get('role')
                if selected_role:
                    role_text_mapping = {
                        "admin": "🔑 Администратор",
                        "smm_manager": "📱 СММ-менеджер",
                        "designer": "🎨 Дизайнер"
                    }
                    role_text = role_text_mapping.get(selected_role, "")
                    if role_text:
                        await self.handle_archived_tasks_role_selection(update, context, role_text)
                return True

            if text in ["📅 За сегодня", "📅 За неделю", "📅 За месяц", "📅 За все время"]:
                await self.handle_archived_tasks_period_selection(update, context, text)
                return True

        # Обработка общих кнопок "Назад"
        elif text == "🔙 Назад" and (active_tasks_data or archived_tasks_data):
            # Возвращаемся к началу просмотра задач
            if active_tasks_data:
                await self.handle_active_tasks_start(update, context)
            elif archived_tasks_data:
                await self.handle_archived_tasks_start(update, context)
            return True

        return False  # Сообщение не обработано

    async def send_task_notification(self, executor_telegram_id: int, task_id: int, task_data: dict):
        """Отправка уведомления исполнителю о новой задаче"""
        logger.info(f"🔔 send_task_notification вызвана: task_id={task_id}, executor_telegram_id={executor_telegram_id}")
        try:
            # Формируем сообщение о новой задаче
            notification_text = f"""
🔔 **Вам назначена новая задача!**

📋 **Задача #{task_id}**
┌─────────────────────────────────┐
│ 📝 **Название:** {task_data.get('title')}
│ 📁 **Проект:** {task_data.get('project_name', 'Не указан')}
│ 🏷️ **Тип:** {self.get_task_type_name(task_data.get('task_type', ''))}
"""

            if task_data.get('format'):
                notification_text += f"│ 📐 **Формат:** {task_data.get('format')}\n"

            notification_text += f"│ ⏰ **Дедлайн:** {task_data.get('deadline_text', 'Не установлен')}\n"
            notification_text += "└─────────────────────────────────┘\n\n"
            notification_text += "💡 **Нажмите кнопку ниже, чтобы принять задачу в работу**"

            # Создаем inline кнопку "Принять в работу"
            inline_keyboard = [
                [InlineKeyboardButton("✅ Принять в работу", callback_data=f"accept_task_{task_id}")]
            ]
            inline_markup = InlineKeyboardMarkup(inline_keyboard)

            # Отправляем уведомление исполнителю в личные сообщения
            if self.bot.app:
                try:
                    await self.bot.app.bot.send_message(
                        chat_id=executor_telegram_id,
                        text=notification_text,
                        parse_mode='Markdown',
                        reply_markup=inline_markup
                    )
                    logger.info(f"✅ Уведомление о задаче #{task_id} отправлено в личные сообщения пользователю {executor_telegram_id}")
                except Exception as send_error:
                    error_msg = str(send_error)
                    if "bot was blocked by the user" in error_msg or "user is deactivated" in error_msg:
                        logger.warning(f"⚠️ Не удалось отправить уведомление пользователю {executor_telegram_id}: пользователь заблокировал бота")
                    elif "chat not found" in error_msg:
                        logger.warning(f"⚠️ Не удалось отправить уведомление пользователю {executor_telegram_id}: пользователь не начал разговор с ботом (/start)")
                    else:
                        logger.error(f"❌ Ошибка отправки уведомления пользователю {executor_telegram_id}: {send_error}")
            else:
                logger.error("Bot application is not initialized")

        except Exception as e:
            logger.error(f"Ошибка при формировании уведомления о задаче: {e}")

    async def handle_new_tasks_start(self, update, context):
        """Просмотр непринятых задач (статус 'new')"""
        # Получаем текущего пользователя
        user = update.effective_user
        db_user = self.bot.get_user_by_telegram_id(user.id, user.username)

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return

        conn = self.bot.get_db_connection()
        if not conn:
            await update.message.reply_text("❌ Ошибка подключения к базе данных")
            return

        try:
            # Показываем только задачи, назначенные на текущего пользователя
            cursor = conn.execute("""
                SELECT t.id, t.title, t.description, t.project, t.task_type, t.deadline,
                       t.created_at, u.name as executor_name, u.id as executor_id
                FROM tasks t
                LEFT JOIN users u ON t.executor_id = u.id
                WHERE t.status = 'new' AND t.executor_id = ?
                ORDER BY t.created_at DESC
            """, (db_user['id'],))
            tasks = cursor.fetchall()
            conn.close()

            if not tasks:
                # Получаем роль текущего пользователя для определения кнопок
                keyboard = [
                    ["🔧 Управление задачами"],
                    ["💰 Расходы"],
                    ["🏠 Главное меню", "🗑️ Очистить историю сообщений"]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                await update.message.reply_text(
                    "🎉 **Нет непринятых задач!**\n\n"
                    "Все задачи приняты в работу.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return

            # Отправляем каждую задачу отдельным сообщением с inline кнопкой
            for i, task in enumerate(tasks, 1):
                task_id, title, description, project, task_type, deadline, created_at, executor_name, executor_id = task

                # Формируем информацию о задаче
                task_info = []
                task_info.append(f"🆕 **Задача #{task_id}**")
                task_info.append(f"📝 **Название:** {title}")

                if executor_name:
                    task_info.append(f"👤 **Исполнитель:** {executor_name}")

                if project:
                    task_info.append(f"📁 **Проект:** {project}")

                if task_type:
                    task_info.append(f"🏷️ **Тип:** {task_type}")

                # Форматируем дедлайн
                if deadline:
                    from datetime import datetime
                    try:
                        dl = datetime.fromisoformat(deadline)
                        deadline_str = dl.strftime("%d.%m.%Y в %H:%M")
                        task_info.append(f"⏰ **Дедлайн:** {deadline_str}")

                        # Показываем статус всегда "Новая"
                        task_info.append("🔵 **Статус:** Новая")
                    except:
                        task_info.append(f"⏰ **Дедлайн:** {deadline}")

                # Описание
                if description:
                    desc = description
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    task_info.append(f"📄 **Описание:**\n{desc}")

                # Дата создания
                if created_at:
                    try:
                        from datetime import datetime
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_str = created_dt.strftime("%d.%m.%Y")
                        task_info.append(f"📅 **Создано:** {created_str}")
                    except:
                        pass

                task_message = "\n".join(task_info)

                # Проверяем, последняя ли это задача
                is_last_task = (i == len(tasks))

                # Создаем inline кнопку "Принять в работу"
                inline_keyboard = [
                    [
                        InlineKeyboardButton("✅ Принять в работу", callback_data=f"accept_task_{task_id}")
                    ]
                ]
                inline_markup = InlineKeyboardMarkup(inline_keyboard)

                # Отправляем задачу с inline кнопкой
                await update.message.reply_text(
                    task_message,
                    parse_mode='Markdown',
                    reply_markup=inline_markup
                )

                # Если это последняя задача, добавляем клавиатуру главного меню
                if is_last_task:
                    # Клавиатура с кнопками
                    keyboard = [
                        ["🔧 Управление задачами"],
                        ["💰 Расходы"],
                        ["🏠 Главное меню", "🗑️ Очистить историю сообщений"]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

                    # Отправляем сводное сообщение
                    summary_text = f"📊 **Всего непринятых задач:** {len(tasks)}"

                    await update.message.reply_text(
                        summary_text,
                        parse_mode='Markdown'
                    )

                    # Отправляем информационное сообщение с клавиатурой
                    await update.message.reply_text(
                        "📌 Выберите действие:",
                        reply_markup=reply_markup
                    )
                else:
                    # Небольшая задержка между задачами
                    await asyncio.sleep(0.3)

        except Exception as e:
            logger.error(f"Ошибка при получении непринятых задач: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении задач",
                reply_markup=ReplyKeyboardRemove()
            )
