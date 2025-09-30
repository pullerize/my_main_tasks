#!/usr/bin/env python3

"""
Обработчики задач для Telegram бота
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class TaskHandlers:
    """Класс для обработки операций с задачами"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_project_selection(self, update, context, project_text):
        """Обработка выбора проекта"""

        # Получаем название проекта из базы
        conn = self.get_db_connection()
        if not conn:
            await query.answer("Ошибка подключения к базе данных")
            return

        cursor = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
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

        # Создаем кнопки с типами задач
        task_types = [
            ("🎨 Креативная", "creative"),
            ("📝 Контент", "content"),
            ("🔧 Техническая", "technical"),
            ("📊 Аналитическая", "analytics"),
            ("📞 Общение", "communication"),
            ("🎬 Видео", "video")
        ]

        keyboard = []
        for type_name, type_key in task_types:
            keyboard.append([InlineKeyboardButton(
                type_name,
                callback_data=f"select_task_type_{type_key}"
            )])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_user_{task_data['executor_id']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "➕ **Создание новой задачи**\n\n"
            f"📁 **Проект:** {project['name']}\n\n"
            "🏷️ **Выберите тип задачи:**",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_task_type_selection(self, query, context):
        """Обработка выбора типа задачи"""
        task_type = query.data.replace("select_task_type_", "")

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['task_type'] = task_type

        # Проверяем, нужно ли выбирать формат (только для дизайнеров)
        if task_data['role'] == 'designer':
            task_data['step'] = 'format_selection'
            context.user_data['task_creation'] = task_data

            # Создаем кнопки с форматами для дизайнеров
            formats = [
                ("🖼️ Статика", "static"),
                ("🎬 Видео", "video"),
                ("📱 Stories", "stories"),
                ("🎠 Карусель", "carousel"),
                ("📄 Презентация", "presentation"),
                ("🎨 Иллюстрация", "illustration")
            ]

            keyboard = []
            for format_name, format_key in formats:
                keyboard.append([InlineKeyboardButton(
                    format_name,
                    callback_data=f"select_format_{format_key}"
                )])

            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"select_project_{task_data.get('project_id', 1)}")])
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
            # Для не-дизайнеров сразу переходим к вводу деталей
            task_data['step'] = 'task_details'
            context.user_data['task_creation'] = task_data
            await self.handle_task_details_input(update, context)

    async def handle_format_selection(self, query, context):
        """Обработка выбора формата (только для дизайнеров)"""
        task_format = query.data.replace("select_format_", "")

        # Обновляем данные задачи
        task_data = context.user_data.get('task_creation', {})
        task_data['task_format'] = task_format
        task_data['step'] = 'task_details'
        context.user_data['task_creation'] = task_data

        await self.handle_task_details_input(update, context)

    async def handle_task_details_input(self, update, context):
        """Запрос ввода названия и описания задачи"""
        task_data = context.user_data.get('task_creation', {})

        # Формируем сообщение с выбранными параметрами
        role_names = {
            'designer': 'Дизайнер',
            'smm_manager': 'СММ-менеджер'
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
        message += f"👤 **Роль:** {role_names.get(task_data['role'], task_data['role'])}\n"
        message += f"📁 **Проект:** {task_data['project']}\n"
        message += f"🏷️ **Тип:** {type_names.get(task_data['task_type'], task_data['task_type'])}\n"

        if task_data.get('task_format'):
            message += f"🎨 **Формат:** {format_names.get(task_data['task_format'], task_data['task_format'])}\n"

        message += "\n📝 **Теперь напишите название задачи и описание в следующем формате:**\n\n"
        message += "```\nНазвание задачи\n---\nОписание задачи (опционально)\n```"

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_task")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Устанавливаем состояние ожидания ввода текста
        task_data['step'] = 'awaiting_text_input'
        context.user_data['task_creation'] = task_data

    async def handle_set_deadline(self, query, context):
        """Обработка установки дедлайна"""
        message = (
            "⏰ **Установка дедлайна**\n\n"
            "Введите дедлайн в формате:\n"
            "`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "**Пример:** `25.12.2024 15:30`\n\n"
            "Или выберите быстрые варианты:"
        )

        from datetime import datetime, timedelta
        now = datetime.now()

        keyboard = [
            [InlineKeyboardButton("📅 Сегодня 18:00", callback_data="deadline_today_18")],
            [InlineKeyboardButton("📅 Завтра 12:00", callback_data="deadline_tomorrow_12")],
            [InlineKeyboardButton("📅 Через 3 дня 18:00", callback_data="deadline_3days_18")],
            [InlineKeyboardButton("📅 Через неделю 12:00", callback_data="deadline_week_12")],
            [InlineKeyboardButton("🔙 Назад", callback_data="confirm_task_preview")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)

        # Устанавливаем состояние ожидания ввода дедлайна
        task_data = context.user_data.get('task_creation', {})
        task_data['step'] = 'awaiting_deadline_input'
        context.user_data['task_creation'] = task_data

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