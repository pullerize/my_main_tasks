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

    async def handle_admin_task_management(self, update, context):
        """Меню управления задачами для администратора"""
        keyboard = [
            ["➕ Создать задачу"],
            ["📋 Активные задачи", "📁 Архив задач"],
            ["🔧 Управление задачами"],
            ["💰 Расходы", "📊 Отчеты"]
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
        print(f"🔍 DEBUG: Role selection text called with message='{message_text}'")

        # Сопоставление текста кнопок с ролями
        role_mapping = {
            "🔑 Администратор": "admin",
            "📱 СММ-менеджер": "smm_manager",
            "🎨 Дизайнер": "designer"
        }

        role = role_mapping.get(message_text)
        if not role:
            print(f"❌ DEBUG: Invalid role text '{message_text}'")
            return

        print(f"✅ DEBUG: Valid role '{role}' selected from text '{message_text}'")

        # Продолжаем с той же логикой, что и в callback версии
        await self._process_role_selection(update, context, role, is_callback=False)

    async def handle_role_selection(self, query, context):
        """Обработка выбора роли исполнителя через callback query"""
        # Извлекаем роль из callback data
        role = query.data.replace("select_role_", "")
        print(f"🔍 DEBUG: Role selection called with role='{role}', callback_data='{query.data}'")

        # Проверяем корректность роли
        valid_roles = ['admin', 'designer', 'smm_manager', 'digital']
        if role not in valid_roles:
            print(f"❌ DEBUG: Invalid role '{role}', valid roles: {valid_roles}")
            await query.answer("❌ Неверная роль")
            return

        print(f"✅ DEBUG: Valid role '{role}' selected")

        # Продолжаем с той же логикой
        await self._process_role_selection(query, context, role, is_callback=True)

    async def handle_executor_selection_text(self, update, context):
        """Обработка выбора исполнителя через текстовое сообщение"""
        message_text = update.message.text
        print(f"🔍 DEBUG: Executor selection text called with message='{message_text}'")

        # Извлекаем имя исполнителя из текста кнопки
        if not message_text.startswith("👤 "):
            print(f"❌ DEBUG: Invalid executor text format '{message_text}'")
            return

        executor_name = message_text[2:].strip()  # Убираем "👤 " в начале
        print(f"✅ DEBUG: Looking for executor with name '{executor_name}'")

        # Получаем данные задачи
        task_data = context.user_data.get('admin_task_creation', {})
        role = task_data.get('executor_role')

        if not role:
            print(f"❌ DEBUG: No role found in task_data")
            return

        # Получаем всех пользователей этой роли
        users = await self.get_users_by_role(role)

        # Ищем пользователя по имени
        executor = None
        for user in users:
            if user['name'] == executor_name:
                executor = user
                break

        if not executor:
            print(f"❌ DEBUG: Executor '{executor_name}' not found")
            await update.message.reply_text("❌ Исполнитель не найден")
            return

        print(f"✅ DEBUG: Found executor: {executor}")

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

        # Получаем все проекты
        projects = await self.get_all_projects()

        if not projects:
            await update.message.reply_text(
                f"❌ **Нет доступных проектов**\n\n"
                "Обратитесь к администратору для создания проектов.",
                parse_mode='Markdown'
            )
            return

        # Создаем обычные кнопки клавиатуры с проектами (по 2 в ряд)
        keyboard = []
        project_buttons = [f"📁 {project['name']}" for project in projects]
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
        print(f"🔍 DEBUG: Project selection text called with message='{message_text}'")

        # Извлекаем название проекта из текста кнопки
        if not message_text.startswith("📁 "):
            print(f"❌ DEBUG: Invalid project text format '{message_text}'")
            return

        project_name = message_text[2:].strip()  # Убираем "📁 " в начале
        print(f"✅ DEBUG: Looking for project with name '{project_name}'")

        # Получаем все проекты
        projects = await self.get_all_projects()

        # Ищем проект по имени
        project = None
        for proj in projects:
            if proj['name'] == project_name:
                project = proj
                break

        if not project:
            print(f"❌ DEBUG: Project '{project_name}' not found")
            await update.message.reply_text("❌ Проект не найден")
            return

        print(f"✅ DEBUG: Found project: {project}")

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
        print(f"🔍 DEBUG: Task type selection text called with message='{message_text}'")

        task_data = context.user_data.get('admin_task_creation', {})
        executor_role = task_data.get('executor_role')

        # Получаем доступные типы задач для роли из API
        available_task_types = await self.get_task_types_by_role(executor_role)

        if message_text not in available_task_types:
            print(f"❌ DEBUG: Invalid task type text '{message_text}', available: {available_task_types}")
            return

        print(f"✅ DEBUG: Valid task type '{message_text}' selected from available types")

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
            print(f"❌ ERROR: Failed to get formats from API: {e}")
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
        print(f"🔍 DEBUG: Format selection text called with message='{message_text}'")

        # Получаем доступные форматы из API
        try:
            formats_data = await self.bot.get_task_formats_from_api()
            if formats_data:
                available_formats = [display_name for display_name, internal_name in formats_data]
            else:
                available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]
        except Exception as e:
            print(f"❌ ERROR: Failed to get formats from API: {e}")
            available_formats = ["📱 9:16", "⬜ 1:1", "📐 4:5", "📺 16:9", "🔄 Другое"]

        if message_text not in available_formats:
            print(f"❌ DEBUG: Invalid format text '{message_text}', available: {available_formats}")
            return

        print(f"✅ DEBUG: Valid format '{message_text}' selected")

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

    async def _process_role_selection(self, update_or_query, context, role, is_callback=True):
        """Общая логика обработки выбора роли"""

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
        task_data['executor_role'] = role
        task_data['step'] = 'executor_selection'
        context.user_data['admin_task_creation'] = task_data

        # Получаем пользователей этой роли
        users = await self.get_users_by_role(role)
        print(f"👥 DEBUG: Found {len(users)} users for role '{role}'")
        for user in users:
            print(f"   - {user}")

        if not users:
            print(f"❌ DEBUG: No users found for role '{role}'")
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

        # Создаем обычные кнопки клавиатуры с исполнителями (по 3 в ряд)
        keyboard = []
        user_buttons = [f"👤 {user['name']}" for user in users]
        for i in range(0, len(user_buttons), 3):
            row = user_buttons[i:i+3]
            keyboard.append(row)

        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

        role_name = self.get_role_name(role)
        message_text = (
            f"➕ **Создание новой задачи**\n\n"
            f"👥 **Роль:** {role_name}\n\n"
            f"👤 **Выберите исполнителя:**"
        )

        if is_callback:
            await update_or_query.edit_message_text(
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
        context.user_data['admin_task_creation'] = task_data

        # Получаем все проекты
        projects = await self.get_all_projects()

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

        # Создаем inline кнопки с проектами
        keyboard = []
        for project in projects:
            keyboard.append([InlineKeyboardButton(
                f"📁 {project['name']}",
                callback_data=f"select_project_{project['id']}"
            )])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_role_{task_data.get('executor_role')}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"➕ **Создание новой задачи**\n\n"
            f"👤 **Исполнитель:** {executor['name']}\n\n"
            f"📁 **Выберите проект:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_project_selection(self, query, context):
        """Обработка выбора проекта через callback query"""
        # Извлекаем ID проекта из callback data
        project_id = int(query.data.replace("select_project_", ""))

        # Находим проект по ID
        projects = await self.get_all_projects()
        project = None
        for proj in projects:
            if proj['id'] == project_id:
                project = proj
                break

        if not project:
            await query.answer("❌ Проект не найден")
            return

        # Обновляем данные создания задачи
        task_data = context.user_data.get('admin_task_creation', {})
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
            conn.close()

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

            # Создаем главное меню
            keyboard = [
                ["🔧 Управление задачами"],
                ["💰 Расходы", "📊 Отчеты"]
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
        """Получение пользователей по роли"""
        print(f"🔍 DEBUG: get_users_by_role called with role='{role}'")
        try:
            conn = self.bot.get_db_connection()
            if not conn:
                print("❌ DEBUG: Failed to get database connection")
                return []

            print(f"✅ DEBUG: Database connection successful")
            cursor = conn.execute("""
                SELECT id, name, telegram_username
                FROM users
                WHERE role = ? AND is_active = 1
                ORDER BY name
            """, (role,))
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            print(f"👥 DEBUG: Query returned {len(users)} users")
            return users
        except Exception as e:
            print(f"❌ DEBUG: Exception in get_users_by_role: {e}")
            logger.error(f"Ошибка получения пользователей: {e}")
            if 'conn' in locals():
                conn.close()
            return []

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        conn = self.bot.get_db_connection()
        if not conn:
            return None

        try:
            cursor = conn.execute("""
                SELECT id, name, telegram_username, role
                FROM users
                WHERE id = ?
            """, (user_id,))
            user = cursor.fetchone()
            conn.close()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            conn.close()
            return None

    async def get_all_projects(self) -> List[Dict]:
        """Получение всех проектов"""
        conn = self.bot.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute("""
                SELECT id, name
                FROM projects
                WHERE is_archived = 0
                ORDER BY start_date DESC
            """)
            projects = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return projects
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
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
            # Используем метод bot для получения типов задач из API
            task_types_data = await self.bot.get_task_types_from_api(role)

            if task_types_data:
                # Возвращаем список названий для кнопок клавиатуры
                # API возвращает список кортежей: [(display_name, internal_name), ...]
                return [display_name for display_name, internal_name in task_types_data]
            else:
                # Fallback к статическим типам при ошибке API
                return self.get_fallback_task_types_by_role(role)

        except Exception as e:
            print(f"❌ ERROR: Failed to get task types from API: {e}")
            # Fallback к статическим типам при ошибке
            return self.get_fallback_task_types_by_role(role)

    def get_fallback_task_types_by_role(self, role: str) -> List[str]:
        """Fallback статические типы задач в зависимости от роли"""
        task_types = {
            'designer': [
                "🎬 Motion",
                "🖼️ Статика",
                "📹 Видео",
                "🎠 Карусель",
                "🔄 Другое"
            ],
            'smm_manager': [
                "📝 Публикация",
                "📅 Контент план",
                "📊 Отчет",
                "📸 Съемка",
                "🤝 Встреча",
                "📈 Стратегия",
                "📋 Презентация",
                "⚙️ Админ задачи",
                "🔍 Анализ",
                "📑 Брифинг",
                "📝 Сценарий",
                "🔄 Другое"
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
        print(f"DEBUG: Found {len(users)} users for role '{role}'")

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

            # Получаем активные задачи пользователя (только статус "В работе")
            cursor = conn.execute("""
                SELECT id, title, description, project, task_type, deadline, created_at
                FROM tasks
                WHERE executor_id = ? AND status = 'in_progress'
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
                        ["💰 Расходы", "📊 Отчеты"]
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

            # Отправляем сводное сообщение
            summary_text = (
                f"📋 **Активные задачи: {user['name']}**\n"
                f"👥 **Роль:** {self.get_role_display_name(user.get('role', 'unknown'))}\n"
                f"📊 **Всего активных задач:** {len(tasks)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            await update.message.reply_text(
                summary_text,
                parse_mode='Markdown'
            )

            # Небольшая задержка перед отправкой задач
            await asyncio.sleep(0.5)

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
                            ["💰 Расходы", "📊 Отчеты"]
                        ]
                    else:
                        keyboard = [
                            ["🔧 Управление задачами"],
                            ["💰 Расходы"]
                        ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

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
                        ["💰 Расходы", "📊 Отчеты"]
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
                    ["💰 Расходы", "📊 Отчеты"]
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
            print(f"DEBUG: Found {len(rows)} users for role '{role_key}'")
            for row in rows:
                users.append({
                    'id': row[0],
                    'name': row[1],
                    'telegram_username': row[2],
                    'role': row[3]
                })
                print(f"DEBUG: User {row[1]} (id: {row[0]})")

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

    async def handle_admin_message(self, update, context, text):
        """Централизованная обработка администраторских сообщений"""
        print(f"DEBUG: Admin message handler called with text: '{text}'")
        print(f"DEBUG: User ID: {update.effective_user.id}, Username: @{update.effective_user.username}")

        # Обработка workflow активных задач
        active_tasks_data = context.user_data.get('active_tasks_view')
        print(f"DEBUG: Active tasks data: {active_tasks_data}")

        # Дебаг всех данных пользователя
        print(f"DEBUG: All user_data keys: {list(context.user_data.keys())}")

        # Дополнительная отладка для понимания проблемы
        if text in ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер"]:
            print(f"DEBUG: Role button pressed: '{text}'")
            print(f"DEBUG: Active tasks data exists: {active_tasks_data is not None}")
            if active_tasks_data:
                print(f"DEBUG: Current step: {active_tasks_data.get('step')}")
                print(f"DEBUG: Step matches role_selection: {active_tasks_data.get('step') == 'role_selection'}")
            else:
                print(f"DEBUG: No active_tasks_data found - workflow not started properly")

        # Начало просмотра активных задач
        if text == "📋 Активные задачи":
            print(f"DEBUG: Starting active tasks workflow")
            await self.handle_active_tasks_start(update, context)
            return True

        # Обработка выбора роли в активных задачах
        elif active_tasks_data and active_tasks_data.get('step') == 'role_selection':
            print(f"DEBUG: Active tasks role selection. Text: '{text}', Step: {active_tasks_data.get('step')}")
            if text in ["🔑 Администратор", "📱 СММ-менеджер", "🎨 Дизайнер"]:
                print(f"DEBUG: Role selected: {text}")
                print(f"DEBUG: About to call handle_active_tasks_role_selection")
                try:
                    await self.handle_active_tasks_role_selection(update, context, text)
                    print(f"DEBUG: handle_active_tasks_role_selection completed successfully")
                    return True
                except Exception as e:
                    print(f"DEBUG: Error in handle_active_tasks_role_selection: {e}")
                    return True
            elif text == "📋 Все активные задачи":
                print(f"DEBUG: Showing all active tasks")
                await self.show_all_active_tasks(update, context)
                return True

        # Обработка выбора исполнителя в активных задачах
        elif active_tasks_data and active_tasks_data.get('step') == 'user_selection':
            print(f"DEBUG: User selection step, text: '{text}'")
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

        # Обработка общих кнопок "Назад"
        elif text == "🔙 Назад" and active_tasks_data:
            # Возвращаемся к началу просмотра активных задач
            await self.handle_active_tasks_start(update, context)
            return True

        return False  # Сообщение не обработано
