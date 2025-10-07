"""
Обработчики функций управления задачами для обычных пользователей (SMM менеджеры и дизайнеры)
"""

import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from markdown_utils import escape_markdown

logger = logging.getLogger(__name__)

class UserTaskHandlers:
    """Класс для обработки функций управления задачами для обычных пользователей"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_user_task_management(self, update, context):
        """Меню управления задачами для обычных пользователей"""
        keyboard = [
            ["➕ Создать задачу"],
            ["📋 Активные задачи", "✅ Завершенные задачи"],
            ["🆕 Не принятые в работу"],
            ["🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📋 **Управление задачами** 📋\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    def get_allowed_roles_for_user(self, user_role):
        """Возвращает список ролей, которым пользователь может назначать задачи"""
        if user_role == 'smm_manager':
            return ['smm_manager', 'designer']
        elif user_role == 'designer':
            return ['designer', 'smm_manager']
        return []

    def get_role_display_name(self, role):
        """Получить отображаемое имя роли"""
        role_names = {
            'admin': 'Администратор',
            'smm_manager': 'СММ-менеджер',
            'designer': 'Дизайнер',
            'head_smm': 'Главный СММ'
        }
        return role_names.get(role, role)

    async def handle_user_create_task(self, update, context):
        """Начало создания задачи обычным пользователем"""
        user = update.message.from_user

        # Получаем информацию о пользователе из БД
        conn = self.bot.get_db_connection()
        if not conn:
            await update.message.reply_text("❌ Ошибка подключения к БД.")
            return

        db_user = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        conn.close()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            return

        user_role = db_user['role']

        # Инициализируем создание задачи
        context.user_data['user_task_creation'] = {
            'creator_id': user.id,
            'creator_role': user_role,
            'step': 'role_selection'
        }

        # Определяем доступные роли
        allowed_roles = self.get_allowed_roles_for_user(user_role)

        # Создаем кнопки с ролями
        role_buttons = []
        role_mapping = {
            'smm_manager': "📱 СММ-менеджер",
            'designer': "🎨 Дизайнер"
        }

        for role in allowed_roles:
            if role in role_mapping:
                role_buttons.append(role_mapping[role])

        # Формируем клавиатуру (по 2 кнопки в ряд)
        keyboard = []
        for i in range(0, len(role_buttons), 2):
            row = role_buttons[i:i+2]
            keyboard.append(row)
        keyboard.append(["❌ Отмена"])

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
            "📱 СММ-менеджер": "smm_manager",
            "🎨 Дизайнер": "designer"
        }

        role = role_mapping.get(message_text)
        if not role:
            return

        # Проверяем, имеет ли пользователь право назначать задачи на эту роль
        task_data = context.user_data.get('user_task_creation', {})
        creator_role = task_data.get('creator_role')
        allowed_roles = self.get_allowed_roles_for_user(creator_role)

        if role not in allowed_roles:
            await update.message.reply_text("❌ У вас нет прав назначать задачи на эту роль.")
            return

        # Продолжаем с выбором исполнителя
        await self._process_role_selection(update, context, role)

    async def _process_role_selection(self, update, context, role):
        """Общая логика обработки выбора роли"""
        # Сохраняем выбранную роль
        context.user_data['user_task_creation']['selected_role'] = role
        context.user_data['user_task_creation']['step'] = 'executor_selection'

        # Получаем список пользователей выбранной роли
        conn = self.bot.get_db_connection()

        users = conn.execute(
            "SELECT id, name, telegram_id FROM users WHERE role = ? AND role != 'inactive' ORDER BY name",
            (role,)
        ).fetchall()

        conn.close()

        if not users:
            await update.message.reply_text(
                f"❌ Нет активных пользователей с ролью {role}"
            )
            return

        # Создаем кнопки с пользователями (по 2 в ряд)
        keyboard = []
        for i in range(0, len(users), 2):
            row = []
            for user in users[i:i+2]:
                row.append(f"👤 {user['name']}")
            keyboard.append(row)
        keyboard.append(["❌ Отмена"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        role_names = {
            'smm_manager': 'СММ-менеджер',
            'designer': 'Дизайнер'
        }

        await update.message.reply_text(
            f"👤 **Выберите исполнителя** ({role_names.get(role, role)}):",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_executor_selection_text(self, update, context):
        """Обработка выбора исполнителя через текстовое сообщение"""
        message_text = update.message.text

        # Извлекаем имя из текста кнопки
        if not message_text.startswith("👤 "):
            return

        executor_name = message_text.replace("👤 ", "")

        # Находим пользователя в БД
        conn = self.bot.get_db_connection()

        task_data = context.user_data.get('user_task_creation', {})
        selected_role = task_data.get('selected_role')

        executor = conn.execute(
            "SELECT * FROM users WHERE name = ? AND role = ?",
            (executor_name, selected_role)
        ).fetchone()

        conn.close()

        if not executor:
            await update.message.reply_text("❌ Пользователь не найден.")
            return

        # Сохраняем исполнителя
        context.user_data['user_task_creation']['executor_id'] = executor['id']
        context.user_data['user_task_creation']['executor_name'] = executor['name']
        context.user_data['user_task_creation']['step'] = 'title'

        # Переходим к вводу названия задачи
        keyboard = [["❌ Отмена"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📝 **Введите название задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_title(self, update, context):
        """Обработка ввода названия задачи"""
        title = update.message.text.strip()

        if not title or title == "❌ Отмена":
            return

        context.user_data['user_task_creation']['title'] = title

        # Если редактируем, возвращаемся к просмотру
        if context.user_data['user_task_creation'].get('return_to_preview'):
            context.user_data['user_task_creation'].pop('return_to_preview', None)
            await self.show_task_preview(update, context)
            return

        context.user_data['user_task_creation']['step'] = 'description'

        keyboard = [
            ["⏭️ Пропустить"],
            ["❌ Отмена"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📄 **Введите описание задачи** (или нажмите Пропустить):",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_description(self, update, context):
        """Обработка ввода описания задачи"""
        description = update.message.text.strip()

        if description == "❌ Отмена":
            return

        if description == "⏭️ Пропустить":
            description = ""

        context.user_data['user_task_creation']['description'] = description
        context.user_data['user_task_creation']['step'] = 'project'

        # Получаем список проектов
        conn = self.bot.get_db_connection()

        projects = conn.execute(
            "SELECT id, name FROM projects WHERE is_archived = 0 ORDER BY name"
        ).fetchall()

        conn.close()

        # Кешируем проекты для избежания повторных запросов
        task_data = context.user_data.get('user_task_creation', {})
        task_data['_cached_projects'] = [dict(row) for row in projects]
        context.user_data['user_task_creation'] = task_data

        # Создаем кнопки с проектами (по 2 в ряд)
        keyboard = []
        for i in range(0, len(projects), 2):
            row = []
            for project in projects[i:i+2]:
                row.append(f"📁 {project['name']}")
            keyboard.append(row)
        keyboard.append(["⏭️ Без проекта"])
        keyboard.append(["❌ Отмена"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📁 **Выберите проект** (или пропустите):",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_project(self, update, context):
        """Обработка выбора проекта"""
        message_text = update.message.text.strip()

        if message_text == "❌ Отмена":
            return

        project_id = None
        project_name = None

        if message_text != "⏭️ Без проекта" and message_text.startswith("📁 "):
            project_name = message_text.replace("📁 ", "").strip()

            # Валидация пустого имени
            if not project_name:
                logger.warning("Empty project name after emoji removal")
                await update.message.reply_text("❌ Некорректное имя проекта")
                return

            # Используем кеш проектов если есть
            task_data = context.user_data.get('user_task_creation', {})
            projects = task_data.get('_cached_projects')

            if not projects:
                # Если кеша нет, запрашиваем из БД
                conn = self.bot.get_db_connection()
                projects = conn.execute(
                    "SELECT id, name FROM projects WHERE is_archived = 0 ORDER BY name"
                ).fetchall()
                conn.close()
                # Кешируем для будущих запросов
                task_data['_cached_projects'] = [dict(row) for row in projects]
                context.user_data['user_task_creation'] = task_data

            # Оптимизированный поиск O(1)
            projects_map = {p['name'].strip(): p['id'] for p in task_data['_cached_projects']}
            project_id = projects_map.get(project_name)

            if not project_id:
                logger.warning(f"Project '{project_name}' not found")
                await update.message.reply_text("❌ Проект не найден")
                return

        context.user_data['user_task_creation']['project_id'] = project_id
        context.user_data['user_task_creation']['step'] = 'task_type'

        # Получаем роль исполнителя
        task_data = context.user_data.get('user_task_creation', {})
        executor_role = task_data.get('selected_role')

        # Получаем типы задач из API
        task_types = await self.bot.get_task_types_from_api(executor_role)

        # Создаем кнопки с типами задач (по 3 в ряд)
        keyboard = []
        type_buttons = [display_name for display_name, internal_name in task_types]

        for i in range(0, len(type_buttons), 3):
            row = type_buttons[i:i+3]
            keyboard.append(row)
        keyboard.append(["❌ Отмена"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_type(self, update, context):
        """Обработка выбора типа задачи"""
        message_text = update.message.text.strip()

        if message_text == "❌ Отмена":
            return

        task_data = context.user_data.get('user_task_creation', {})
        executor_role = task_data.get('selected_role')

        # Получаем доступные типы задач для роли
        task_types = await self.bot.get_task_types_from_api(executor_role)

        # Извлекаем только названия типов (без иконок) для сравнения
        available_types = {}
        for display_name, internal_name in task_types:
            # Убираем эмодзи и пробелы для создания ключа
            clean_name = display_name.strip()
            available_types[clean_name] = internal_name

        # Проверяем что выбранный тип существует
        if message_text not in available_types:
            return

        # Сохраняем внутреннее название типа
        context.user_data['user_task_creation']['task_type'] = available_types[message_text]

        # Если роль дизайнер, показываем форматы
        if executor_role == 'designer':
            context.user_data['user_task_creation']['step'] = 'format_selection'
            await self.show_format_selection(update, context)
        else:
            context.user_data['user_task_creation']['step'] = 'deadline'
            await self.show_deadline_selection(update, context)

    async def show_format_selection(self, update, context):
        """Показ выбора формата для дизайнера"""
        # Получаем форматы из API
        formats = await self.bot.get_task_formats_from_api()

        # Создаем кнопки с форматами (по 3 в ряд)
        keyboard = []
        format_buttons = [display_name for display_name, internal_name in formats]

        for i in range(0, len(format_buttons), 3):
            row = format_buttons[i:i+3]
            keyboard.append(row)
        keyboard.append(["❌ Отмена"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📐 **Выберите формат задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_format(self, update, context):
        """Обработка выбора формата задачи"""
        message_text = update.message.text.strip()

        if message_text == "❌ Отмена":
            return

        # Получаем доступные форматы
        formats = await self.bot.get_task_formats_from_api()

        # Извлекаем только названия форматов для сравнения
        available_formats = {}
        for display_name, internal_name in formats:
            clean_name = display_name.strip()
            available_formats[clean_name] = internal_name

        # Проверяем что выбранный формат существует
        if message_text not in available_formats:
            return

        # Сохраняем внутреннее название формата
        context.user_data['user_task_creation']['task_format'] = available_formats[message_text]
        context.user_data['user_task_creation']['step'] = 'deadline'

        await self.show_deadline_selection(update, context)

    async def show_deadline_selection(self, update, context):
        """Показ выбора дедлайна"""
        keyboard = [
            ["📅 Сегодня до 18:00"],
            ["🌆 Завтра до 18:00"],
            ["📅 Через 3 дня до 18:00"],
            ["📆 Через неделю до 18:00"],
            ["⏭️ Без дедлайна"],
            ["❌ Отмена"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "📅 **Выберите дедлайн** или введите дату и время в формате:\n• `ДД.ММ.ГГГГ ЧЧ:ММ` (например: 18.09.2025 18:00)",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_deadline(self, update, context):
        """Обработка выбора дедлайна"""
        message_text = update.message.text.strip()

        if message_text == "❌ Отмена":
            return

        deadline = None
        now = datetime.now()

        if message_text == "📅 Сегодня до 18:00":
            deadline = now.replace(hour=18, minute=0, second=0, microsecond=0)
        elif message_text == "🌆 Завтра до 18:00":
            deadline = (now + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        elif message_text == "📅 Через 3 дня до 18:00":
            deadline = (now + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0)
        elif message_text == "📆 Через неделю до 18:00":
            deadline = (now + timedelta(days=7)).replace(hour=18, minute=0, second=0, microsecond=0)
        elif message_text == "⏭️ Без дедлайна":
            deadline = None
        else:
            # Попытка распарсить дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ
            try:
                deadline = datetime.strptime(message_text, "%d.%m.%Y %H:%M")
            except ValueError:
                await update.message.reply_text(
                    "❌ **Неверный формат даты**\n\n"
                    "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\n"
                    "Например: `18.09.2025 18:00`",
                    parse_mode='Markdown'
                )
                return

        context.user_data['user_task_creation']['deadline'] = deadline.isoformat() if deadline else None

        # Форматируем дедлайн для отображения
        if deadline:
            context.user_data['user_task_creation']['deadline_text'] = deadline.strftime("%d.%m.%Y в %H:%M")
        else:
            context.user_data['user_task_creation']['deadline_text'] = "Не установлен"

        # Показываем предпросмотр задачи
        await self.show_task_preview(update, context)

    async def show_task_preview(self, update, context):
        """Показ предварительного просмотра задачи"""
        task_data = context.user_data.get('user_task_creation', {})

        # Получаем название проекта если есть
        project_name = "Не выбран"
        if task_data.get('project_id'):
            conn = self.bot.get_db_connection()
            project = conn.execute(
                "SELECT name FROM projects WHERE id = ?",
                (task_data['project_id'],)
            ).fetchone()
            conn.close()
            if project:
                project_name = project['name']

        # Экранируем все пользовательские данные
        safe_title = escape_markdown(task_data.get('title', 'Не указано'))
        safe_executor = escape_markdown(task_data.get('executor_name', 'Не выбран'))
        safe_project = escape_markdown(project_name)
        safe_type = escape_markdown(task_data.get('task_type', 'Не указан'))
        safe_format = escape_markdown(task_data.get('task_format', '')) if task_data.get('task_format') else ''
        safe_deadline = escape_markdown(task_data.get('deadline_text', 'Не установлен'))

        # Формируем красивый вывод
        preview_text = f"""
📋 **Предварительный просмотр задачи**

┌─────────────────────────────────┐
│ 📝 **Название:** {safe_title}
│ 👤 **Исполнитель:** {safe_executor}
│ 📁 **Проект:** {safe_project}
│ 🏷️ **Тип:** {safe_type}
"""

        if task_data.get('task_format'):
            preview_text += f"│ 📐 **Формат:** {safe_format}\n"

        preview_text += f"│ ⏰ **Дедлайн:** {safe_deadline}\n"

        if task_data.get('description'):
            desc = task_data['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            safe_desc = escape_markdown(desc)
            preview_text += f"│ 📄 **Описание:** {safe_desc}\n"

        preview_text += "└─────────────────────────────────┘"

        keyboard = [
            ["✅ Создать задачу"],
            ["✏️ Редактировать", "❌ Отмена"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            preview_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Обновляем шаг
        task_data['step'] = 'final_confirmation'
        context.user_data['user_task_creation'] = task_data

    async def handle_task_confirmation(self, update, context):
        """Обработка подтверждения создания задачи"""
        message_text = update.message.text.strip()

        if message_text == "✅ Создать задачу":
            await self._save_task(update, context)
        elif message_text == "✏️ Редактировать":
            await self.handle_edit_task(update, context)
        elif message_text == "❌ Отмена":
            context.user_data.pop('user_task_creation', None)
            await self.handle_user_task_management(update, context)

    async def handle_edit_task(self, update, context):
        """Показ меню редактирования задачи"""
        keyboard = [
            ["📝 Название", "👤 Исполнитель"],
            ["📁 Проект", "🏷️ Тип задачи"],
            ["⏰ Дедлайн", "📄 Описание"],
            ["🔙 Назад к просмотру"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            "✏️ **Что вы хотите изменить?**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        context.user_data['user_task_creation']['step'] = 'edit_selection'

    async def handle_edit_selection(self, update, context):
        """Обработка выбора поля для редактирования"""
        message_text = update.message.text.strip()
        task_data = context.user_data.get('user_task_creation', {})

        if message_text == "🔙 Назад к просмотру":
            await self.show_task_preview(update, context)
            return

        edit_mapping = {
            "📝 Название": ('title', 'Введите новое название задачи:'),
            "📄 Описание": ('description', 'Введите новое описание задачи (или нажмите Пропустить):'),
            "👤 Исполнитель": ('executor', 'executor_selection'),
            "📁 Проект": ('project', 'project_selection'),
            "🏷️ Тип задачи": ('task_type', 'task_type_selection'),
            "⏰ Дедлайн": ('deadline', 'deadline_selection')
        }

        if message_text in edit_mapping:
            field, next_step = edit_mapping[message_text]
            task_data['editing_field'] = field
            task_data['return_to_preview'] = True

            if field == 'title':
                task_data['step'] = 'title'
                keyboard = [["❌ Отмена"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                await update.message.reply_text(next_step, parse_mode='Markdown', reply_markup=reply_markup)
            elif field == 'description':
                task_data['step'] = 'description'
                keyboard = [["⏭️ Пропустить"], ["❌ Отмена"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                await update.message.reply_text(next_step, parse_mode='Markdown', reply_markup=reply_markup)
            elif field == 'executor':
                task_data['step'] = 'executor_selection'
                # Показываем список исполнителей выбранной роли
                await self._process_role_selection(update, context, task_data['selected_role'])
            elif field == 'project':
                task_data['step'] = 'project'
                # Получаем список проектов
                conn = self.bot.get_db_connection()
                projects = conn.execute(
                    "SELECT id, name FROM projects WHERE is_archived = 0 ORDER BY name"
                ).fetchall()
                conn.close()

                keyboard = []
                for i in range(0, len(projects), 2):
                    row = []
                    for project in projects[i:i+2]:
                        row.append(f"📁 {project['name']}")
                    keyboard.append(row)
                keyboard.append(["⏭️ Без проекта"])
                keyboard.append(["❌ Отмена"])

                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                await update.message.reply_text("📁 **Выберите проект** (или пропустите):", parse_mode='Markdown', reply_markup=reply_markup)
            elif field == 'task_type':
                task_data['step'] = 'task_type'
                # Получаем типы задач из API
                task_types = await self.bot.get_task_types_from_api(task_data.get('selected_role'))
                keyboard = []
                type_buttons = [display_name for display_name, internal_name in task_types]
                for i in range(0, len(type_buttons), 3):
                    row = type_buttons[i:i+3]
                    keyboard.append(row)
                keyboard.append(["❌ Отмена"])
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
                await update.message.reply_text("🏷️ **Выберите тип задачи:**", parse_mode='Markdown', reply_markup=reply_markup)
            elif field == 'deadline':
                task_data['step'] = 'deadline'
                await self.show_deadline_selection(update, context)

            context.user_data['user_task_creation'] = task_data

    async def _save_task(self, update, context):
        """Сохранение задачи в БД"""
        task_data = context.user_data.get('user_task_creation', {})

        conn = self.bot.get_db_connection()

        try:
            # Получаем ID создателя из БД
            creator_telegram_id = task_data['creator_id']
            creator = conn.execute(
                "SELECT id FROM users WHERE telegram_id = ?",
                (creator_telegram_id,)
            ).fetchone()

            if not creator:
                await update.message.reply_text("❌ Ошибка: создатель задачи не найден.")
                return

            creator_id = creator[0]

            # Получаем название проекта если есть project_id
            project_name = None
            if task_data.get('project_id'):
                project = conn.execute(
                    "SELECT name FROM projects WHERE id = ?",
                    (task_data['project_id'],)
                ).fetchone()
                if project:
                    project_name = project['name']

            # Вставляем задачу
            cursor = conn.execute("""
                INSERT INTO tasks (
                    title, description, project, task_type, task_format, deadline,
                    author_id, executor_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['title'],
                task_data.get('description', ''),
                project_name,  # Название проекта, а не ID
                task_data['task_type'],
                task_data.get('task_format'),  # Формат для дизайнеров
                task_data.get('deadline'),
                creator_id,
                task_data['executor_id'],
                'new',
                datetime.now().isoformat()
            ))

            task_id = cursor.lastrowid
            conn.commit()

            # Экранируем все пользовательские данные
            safe_title = escape_markdown(task_data.get('title'))
            safe_executor = escape_markdown(task_data.get('executor_name'))
            safe_project = escape_markdown(project_name if project_name else 'Не выбран')
            safe_type = escape_markdown(task_data.get('task_type'))
            safe_format = escape_markdown(task_data.get('task_format', '')) if task_data.get('task_format') else ''
            safe_deadline = escape_markdown(task_data.get('deadline_text', 'Не установлен'))

            # Формируем сообщение об успехе
            success_message = f"""
✅ **Задача успешно создана!**

📋 **Задача #{task_id}**
┌─────────────────────────────────┐
│ 📝 **Название:** {safe_title}
│ 👤 **Исполнитель:** {safe_executor}
│ 📁 **Проект:** {safe_project}
│ 🏷️ **Тип:** {safe_type}
"""

            if task_data.get('task_format'):
                success_message += f"│ 📐 **Формат:** {safe_format}\n"

            success_message += f"│ ⏰ **Дедлайн:** {safe_deadline}\n"
            success_message += "└─────────────────────────────────┘\n\n"
            success_message += "📲 **Задача отображается в системе и доступна исполнителю.**"

            # Уведомляем исполнителя
            executor_info = conn.execute(
                "SELECT telegram_id, name FROM users WHERE id = ?",
                (task_data['executor_id'],)
            ).fetchone()

            if executor_info and executor_info[0]:
                executor_telegram_id = executor_info[0]

                notification = f"🔔 **Новая задача!**"

                try:
                    await context.bot.send_message(
                        chat_id=executor_telegram_id,
                        text=notification,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {e}")

            # Возвращаемся в главное меню
            keyboard = [
                ["➕ Создать задачу"],
                ["📋 Активные задачи", "✅ Завершенные задачи"],
                ["🏠 Главное меню"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            await update.message.reply_text(
                success_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # Очищаем данные
            context.user_data.pop('user_task_creation', None)

        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при создании задачи: {str(e)}"
            )
        finally:
            conn.close()

    async def handle_active_tasks(self, update, context):
        """Показ активных задач пользователя"""
        user = update.message.from_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id, name, role FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            conn.close()
            return

        # Получаем активные задачи (где пользователь - исполнитель)
        tasks = conn.execute("""
            SELECT t.id, t.title, t.description, t.project, t.task_type, t.deadline, t.created_at, t.task_format
            FROM tasks t
            WHERE t.executor_id = ? AND t.status IN ('new', 'in_progress')
            ORDER BY
                CASE WHEN t.deadline IS NULL THEN 1 ELSE 0 END,
                t.deadline ASC,
                t.created_at DESC
            LIMIT 50
        """, (db_user['id'],)).fetchall()

        conn.close()

        if not tasks:
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы", "🏠 Главное меню"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            await update.message.reply_text(
                "📋 У вас нет активных задач.",
                reply_markup=reply_markup
            )
            return

        # Показываем задачи с inline кнопками (как у админа)
        for i, task in enumerate(tasks, 1):
            task_info = []

            # Экранируем пользовательские данные
            safe_title = escape_markdown(task[1]) if task[1] else ""
            safe_project = escape_markdown(task[3]) if task[3] else ""
            safe_type = escape_markdown(task[4]) if task[4] else ""
            safe_format = escape_markdown(task[7]) if task[7] else ""

            # Заголовок задачи с номером
            task_info.append(f"📝 **Задача #{i}**")
            task_info.append(f"**{safe_title}**")  # title
            task_info.append("─────────────────────")

            # Проект
            if task[3]:  # project
                task_info.append(f"🎯 **Проект:** {safe_project}")

            # Тип задачи
            if task[4]:  # task_type
                task_info.append(f"📂 **Тип:** {safe_type}")

            # Формат задачи (для дизайнеров)
            if task[7]:  # task_format
                task_info.append(f"🎨 **Формат:** {safe_format}")

            # Дедлайн
            if task[5]:  # deadline
                try:
                    deadline_dt = datetime.fromisoformat(task[5].replace('Z', '+00:00'))
                    deadline_str = deadline_dt.strftime("%d.%m.%Y в %H:%M")
                    task_info.append(f"⏰ **Дедлайн:** {deadline_str}")

                    # Статус всегда "В работе" для активных задач
                    task_info.append("🟢 **Статус:** В работе")

                    # Проверяем, сколько времени осталось до дедлайна
                    now = datetime.now()
                    time_left = deadline_dt - now
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
                safe_desc = escape_markdown(desc)
                task_info.append(f"📄 **Описание:**\n{safe_desc}")

            # Дата создания
            if task[6]:  # created_at
                try:
                    created_dt = datetime.fromisoformat(task[6].replace('Z', '+00:00'))
                    created_str = created_dt.strftime("%d.%m.%Y")
                    task_info.append(f"📅 **Создано:** {created_str}")
                except:
                    pass

            task_message = "\n".join(task_info)

            # Создаем inline кнопки для каждой задачи
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

        # После всех задач отправляем сводное сообщение с главным меню
        keyboard = [
            ["🔧 Управление задачами"],
            ["💰 Расходы", "🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        summary_text = (
            f"📋 **Активные задачи: {db_user['name']}**\n"
            f"👥 **Роль:** {self.get_role_display_name(db_user['role'] if db_user['role'] else 'unknown')}\n"
            f"📊 **Всего активных задач:** {len(tasks)}"
        )

        await update.message.reply_text(
            summary_text,
            parse_mode='Markdown'
        )

        await update.message.reply_text(
            "📌 Выберите действие:",
            reply_markup=reply_markup
        )

    async def handle_completed_tasks(self, update, context):
        """Показ завершенных задач пользователя"""
        user = update.message.from_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id, name, role FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            conn.close()
            return

        # Получаем завершенные задачи
        tasks = conn.execute("""
            SELECT t.id, t.title, t.description, t.project, t.task_type, t.finished_at, t.created_at, t.task_format
            FROM tasks t
            WHERE t.executor_id = ? AND t.status = 'done'
            ORDER BY t.finished_at DESC
            LIMIT 50
        """, (db_user['id'],)).fetchall()

        conn.close()

        if not tasks:
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы", "🏠 Главное меню"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

            await update.message.reply_text(
                "✅ У вас нет завершенных задач.",
                reply_markup=reply_markup
            )
            return

        # Показываем задачи с inline кнопками (как у админа)
        for i, task in enumerate(tasks, 1):
            task_info = []

            # Заголовок задачи с номером
            task_info.append(f"✅ **Задача #{i}**")
            task_info.append(f"**{task[1]}**")  # title
            task_info.append("─────────────────────")

            # Проект
            if task[3]:  # project
                task_info.append(f"🎯 **Проект:** {task[3]}")

            # Тип задачи
            if task[4]:  # task_type
                task_info.append(f"📂 **Тип:** {task[4]}")

            # Формат задачи (для дизайнеров)
            if task[7]:  # task_format
                task_info.append(f"🎨 **Формат:** {task[7]}")

            # Дата завершения
            if task[5]:  # finished_at
                try:
                    finished_dt = datetime.fromisoformat(task[5].replace('Z', '+00:00'))
                    finished_str = finished_dt.strftime("%d.%m.%Y в %H:%M")
                    task_info.append(f"✅ **Завершено:** {finished_str}")
                    task_info.append("🟢 **Статус:** Выполнено")
                except:
                    task_info.append(f"✅ **Завершено:** {task[5]}")

            # Описание
            if task[2]:  # description
                desc = task[2]
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                safe_desc = escape_markdown(desc)
                task_info.append(f"📄 **Описание:**\n{safe_desc}")

            # Дата создания
            if task[6]:  # created_at
                try:
                    created_dt = datetime.fromisoformat(task[6].replace('Z', '+00:00'))
                    created_str = created_dt.strftime("%d.%m.%Y")
                    task_info.append(f"📅 **Создано:** {created_str}")
                except:
                    pass

            task_message = "\n".join(task_info)

            # Создаем inline кнопку для удаления (завершенные задачи можно только удалить)
            inline_keyboard = [
                [
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

        # После всех задач отправляем сводное сообщение с главным меню
        keyboard = [
            ["🔧 Управление задачами"],
            ["💰 Расходы", "🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        summary_text = (
            f"✅ **Завершенные задачи: {db_user['name']}**\n"
            f"👥 **Роль:** {self.get_role_display_name(db_user['role'] if db_user['role'] else 'unknown')}\n"
            f"📊 **Всего завершенных задач:** {len(tasks)}"
        )

        await update.message.reply_text(
            summary_text,
            parse_mode='Markdown'
        )

        await update.message.reply_text(
            "📌 Выберите действие:",
            reply_markup=reply_markup
        )

    async def handle_task_id_input(self, update, context):
        """Обработка ввода ID задачи для управления ею"""
        if not context.user_data.get('awaiting_task_id'):
            return False

        message_text = update.message.text.strip()

        # Проверяем, что это число
        try:
            task_id = int(message_text)
        except ValueError:
            return False

        user = update.message.from_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            conn.close()
            return True

        # Проверяем, что задача существует и пользователь - её исполнитель
        task = conn.execute("""
            SELECT t.*, p.name as project_name, u.name as creator_name
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            LEFT JOIN users u ON t.creator_id = u.id
            WHERE t.id = ? AND t.executor_id = ?
        """, (task_id, db_user['id'])).fetchone()

        conn.close()

        if not task:
            await update.message.reply_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
            context.user_data.pop('awaiting_task_id', None)
            return True

        # Показываем детали задачи и кнопки управления
        deadline_text = "Не указан"
        if task['deadline']:
            try:
                deadline_obj = datetime.fromisoformat(task['deadline'])
                deadline_text = deadline_obj.strftime("%d.%m.%Y")
            except:
                deadline_text = task['deadline']

        project_text = task['project_name'] if task['project_name'] else "Без проекта"
        status_text = {
            'new': '🆕 Новая',
            'in_progress': '⏳ В процессе',
            'done': '✅ Завершена',
            'overdue': '⏰ Просрочена'
        }.get(task['status'], task['status'])

        message = (
            f"📋 **Задача #{task['id']}**\n\n"
            f"📝 {task['title']}\n"
            f"📄 {task['description'] if task['description'] else 'Без описания'}\n\n"
            f"🏷️ Тип: {task['task_type']}\n"
            f"📅 Дедлайн: {deadline_text}\n"
            f"📁 Проект: {project_text}\n"
            f"👤 Создатель: {task['creator_name']}\n"
            f"📊 Статус: {status_text}\n"
        )

        # Кнопки управления (только если задача активна)
        if task['status'] in ('new', 'in_progress'):
            keyboard = [
                ["✅ Завершить задачу"],
                ["🗑️ Удалить задачу"],
                ["🔙 Назад"]
            ]
        else:
            keyboard = [["🔙 Назад"]]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Сохраняем ID задачи для дальнейших действий
        context.user_data['current_task_id'] = task_id
        context.user_data.pop('awaiting_task_id', None)

        return True

    async def handle_complete_task(self, update, context):
        """Завершение задачи"""
        task_id = context.user_data.get('current_task_id')
        if not task_id:
            await update.message.reply_text("❌ Задача не выбрана.")
            return

        user = update.message.from_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            conn.close()
            return

        # Проверяем, что задача существует и пользователь - её исполнитель
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND executor_id = ?",
            (task_id, db_user['id'])
        ).fetchone()

        if not task:
            await update.message.reply_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
            conn.close()
            return

        # Завершаем задачу
        conn.execute("""
            UPDATE tasks
            SET status = 'done', finished_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), task_id))

        conn.commit()
        conn.close()

        # Возвращаемся к списку задач
        keyboard = [
            ["➕ Создать задачу"],
            ["📋 Активные задачи", "✅ Завершенные задачи"],
            ["🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"✅ Задача #{task_id} успешно завершена!",
            reply_markup=reply_markup
        )

        context.user_data.pop('current_task_id', None)

    async def handle_delete_task(self, update, context):
        """Удаление задачи"""
        task_id = context.user_data.get('current_task_id')
        if not task_id:
            await update.message.reply_text("❌ Задача не выбрана.")
            return

        user = update.message.from_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден в системе.")
            conn.close()
            return

        # Проверяем, что задача существует и пользователь - её исполнитель
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND executor_id = ?",
            (task_id, db_user['id'])
        ).fetchone()

        if not task:
            await update.message.reply_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
            conn.close()
            return

        # Удаляем задачу
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()

        # Возвращаемся к списку задач
        keyboard = [
            ["➕ Создать задачу"],
            ["📋 Активные задачи", "✅ Завершенные задачи"],
            ["🏠 Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            f"🗑️ Задача #{task_id} успешно удалена!",
            reply_markup=reply_markup
        )

        context.user_data.pop('current_task_id', None)

    async def handle_task_callback(self, update, context):
        """Обработка inline кнопок для завершения и удаления задач"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user = update.effective_user

        conn = self.bot.get_db_connection()

        # Получаем ID пользователя
        db_user = conn.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (user.id,)
        ).fetchone()

        if not db_user:
            await query.edit_message_text("❌ Пользователь не найден в системе.")
            conn.close()
            return

        if data.startswith("complete_task_"):
            task_id = int(data.replace("complete_task_", ""))

            # Проверяем, что задача существует и пользователь - её исполнитель
            task = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND executor_id = ?",
                (task_id, db_user['id'])
            ).fetchone()

            if not task:
                await query.edit_message_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
                conn.close()
                return

            # Завершаем задачу
            conn.execute(
                "UPDATE tasks SET status = 'done', finished_at = ? WHERE id = ?",
                (datetime.now().isoformat(), task_id)
            )
            conn.commit()
            conn.close()

            # Обновляем сообщение
            await query.edit_message_text(
                f"✅ Задача #{task_id} **{task['title']}** успешно завершена!",
                parse_mode='Markdown'
            )

        elif data.startswith("delete_task_"):
            task_id = int(data.replace("delete_task_", ""))

            # Проверяем, что задача существует и пользователь - её исполнитель
            task = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND executor_id = ?",
                (task_id, db_user['id'])
            ).fetchone()

            if not task:
                await query.edit_message_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
                conn.close()
                return

            # Удаляем задачу
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()

            # Обновляем сообщение
            await query.edit_message_text(
                f"🗑️ Задача #{task_id} **{task['title']}** успешно удалена!",
                parse_mode='Markdown'
            )

        elif data.startswith("accept_task_"):
            task_id = int(data.replace("accept_task_", ""))

            # Проверяем, что задача существует и пользователь - её исполнитель
            task = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND executor_id = ?",
                (task_id, db_user['id'])
            ).fetchone()

            if not task:
                await query.edit_message_text("❌ Задача не найдена или вы не являетесь её исполнителем.")
                conn.close()
                return

            # Принимаем задачу в работу (меняем статус на in_progress)
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', accepted_at = ? WHERE id = ?",
                (datetime.now().isoformat(), task_id)
            )
            conn.commit()
            conn.close()

            # Обновляем сообщение
            await query.edit_message_text(
                f"✅ Задача #{task_id} **{task['title']}** принята в работу!\n\n"
                f"📌 Задача теперь отображается в разделе 'В работе'",
                parse_mode='Markdown'
            )
