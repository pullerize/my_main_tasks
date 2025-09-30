#!/usr/bin/env python3

"""
Обработчики для управления расходами в Telegram боте
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

class ExpenseHandlers:
    """Класс для обработки всех операций с расходами"""

    def __init__(self, bot_instance):
        self.bot = bot_instance

    async def handle_expenses_menu(self, query, context):
        """Главное меню расходов"""
        try:
            user = query.from_user
            db_user = self.bot.get_user_by_telegram_id(user.id, user.username)

            if not db_user:
                await query.edit_message_text(
                    "❌ Пользователь не найден. Пожалуйста, авторизуйтесь заново."
                )
                return

            keyboard = [
                [InlineKeyboardButton("➕ Ввести новый расход", callback_data="add_expense")],
                [InlineKeyboardButton("📋 Посмотреть мои расходы", callback_data="view_expenses")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = f"""
💰 **Управление расходами**

👤 **{db_user['name']}**

**Выберите действие:**
            """

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в handle_expenses_menu: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_add_expense_start(self, query, context):
        """Начало процесса добавления расхода"""
        try:
            # Инициализируем данные для создания расхода
            context.user_data['expense_creation'] = {
                'step': 'name',
                'name': '',
                'amount': '',
                'date': '',
                'project_id': None,
                'description': ''
            }

            message = """
➕ **Новый расход**

**Шаг 1/5:** Введите наименование расхода

📝 *Например: Обед, Транспорт, Канцелярия, Оборудование*

Или нажмите /cancel для отмены
            """

            await query.edit_message_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Ошибка в handle_add_expense_start: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_view_expenses_periods(self, query, context):
        """Выбор периода для просмотра расходов"""
        try:
            keyboard = [
                [InlineKeyboardButton("📅 За день", callback_data="period_day")],
                [InlineKeyboardButton("📅 За неделю", callback_data="period_week")],
                [InlineKeyboardButton("📅 За месяц", callback_data="period_month")],
                [InlineKeyboardButton("📅 За год", callback_data="period_year")],
                [InlineKeyboardButton("🔙 Назад", callback_data="my_expenses")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = """
📋 **Мои расходы**

**Выберите период для просмотра:**
            """

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в handle_view_expenses_periods: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    async def handle_period_selection(self, query, context):
        """Обработка выбора периода и показ расходов"""
        try:
            period = query.data.replace("period_", "")
            user = query.from_user
            db_user = self.bot.get_user_by_telegram_id(user.id, user.username)

            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден.")
                return

            # Определяем даты для периода
            now = datetime.now()
            if period == "day":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                period_name = "сегодня"
            elif period == "week":
                start_date = now - timedelta(days=7)
                period_name = "за неделю"
            elif period == "month":
                start_date = now - timedelta(days=30)
                period_name = "за месяц"
            elif period == "year":
                start_date = now - timedelta(days=365)
                period_name = "за год"
            else:
                start_date = now - timedelta(days=30)
                period_name = "за месяц"

            # Получаем расходы за период
            expenses = self.get_user_expenses_by_period(db_user['id'], start_date)

            if not expenses:
                keyboard = [
                    [InlineKeyboardButton("📅 Выбрать другой период", callback_data="view_expenses")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="my_expenses")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                message = f"""
📋 **Мои расходы {period_name}**

📝 Расходов за этот период не найдено.

**Добавьте новый расход или выберите другой период.**
                """

                await query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return

            # Формируем сообщение с расходами
            total = 0
            message = f"📋 **Мои расходы {period_name}**\n\n"

            for expense in expenses:
                amount = float(expense['amount']) if expense['amount'] else 0
                total += amount

                date_str = expense['date'] if expense['date'] else 'Не указана'
                project_name = expense['project_name'] if expense['project_name'] else 'Без проекта'
                description = expense['description'] if expense['description'] else ''

                message += f"💳 **{expense['name']}**\n"
                message += f"   💰 Сумма: {amount:,.0f} сум\n"
                message += f"   📅 Дата: {date_str}\n"
                message += f"   📁 Проект: {project_name}\n"
                if description:
                    message += f"   💬 Комментарий: {description}\n"
                message += "\n"

            message += f"💎 **Общая сумма: {total:,.0f} сум**"

            keyboard = [
                [InlineKeyboardButton("📅 Выбрать другой период", callback_data="view_expenses")],
                [InlineKeyboardButton("🔙 Назад", callback_data="my_expenses")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в handle_period_selection: {e}")
            await query.edit_message_text("❌ Произошла ошибка при получении расходов.")

    async def handle_expense_text_input(self, update: Update, context):
        """Обработка текстового ввода для создания расхода"""
        if 'expense_creation' not in context.user_data:
            return

        try:
            expense_data = context.user_data['expense_creation']
            text = update.message.text.strip()

            if expense_data['step'] == 'name':
                # Сохраняем наименование
                expense_data['name'] = text
                expense_data['step'] = 'amount'

                message = """
➕ **Новый расход**

**Шаг 2/5:** Введите сумму расхода

💰 *Введите сумму в сумах (только цифры)*

📝 *Например: 50000*

Или нажмите /cancel для отмены
                """

                await update.message.reply_text(message, parse_mode='Markdown')

            elif expense_data['step'] == 'amount':
                # Проверяем и сохраняем сумму
                try:
                    amount = float(text.replace(' ', '').replace(',', ''))
                    if amount <= 0:
                        raise ValueError("Сумма должна быть больше нуля")

                    expense_data['amount'] = amount
                    expense_data['step'] = 'date'

                    # Предлагаем сегодняшнюю дату по умолчанию
                    today = datetime.now().strftime("%d.%m.%Y")

                    message = f"""
➕ **Новый расход**

**Шаг 3/5:** Введите дату расхода

📅 *Введите дату в формате ДД.ММ.ГГГГ*

📝 *Например: {today}*

💡 *Для использования сегодняшней даты просто напишите "сегодня"*

Или нажмите /cancel для отмены
                    """

                    await update.message.reply_text(message, parse_mode='Markdown')

                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверная сумма. Пожалуйста, введите корректную сумму (только цифры).\n\n"
                        "💰 *Например: 50000*",
                        parse_mode='Markdown'
                    )

            elif expense_data['step'] == 'date':
                # Обрабатываем дату
                try:
                    if text.lower() in ['сегодня', 'today']:
                        date_obj = datetime.now()
                    else:
                        date_obj = datetime.strptime(text, "%d.%m.%Y")

                    expense_data['date'] = date_obj.strftime("%Y-%m-%d")
                    expense_data['step'] = 'project'

                    # Показываем выбор проекта
                    await self.show_project_selection(update, context)

                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n\n"
                        "📅 *Например: 25.12.2024 или напишите 'сегодня'*",
                        parse_mode='Markdown'
                    )

            elif expense_data['step'] == 'description':
                # Сохраняем описание и создаем расход
                expense_data['description'] = text
                await self.create_expense(update, context)

        except Exception as e:
            logger.error(f"Ошибка в handle_expense_text_input: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

    async def show_project_selection(self, update, context):
        """Показать выбор проекта"""
        try:
            projects = self.get_projects()

            keyboard = []
            # Добавляем кнопку "Без привязки к проекту"
            keyboard.append([InlineKeyboardButton("❌ Без привязки к проекту", callback_data="project_none")])

            # Добавляем проекты по 2 в ряд
            for i in range(0, len(projects), 2):
                row = []
                for j in range(2):
                    if i + j < len(projects):
                        project = projects[i + j]
                        row.append(InlineKeyboardButton(
                            f"📁 {project['name'][:20]}{'...' if len(project['name']) > 20 else ''}",
                            callback_data=f"project_{project['id']}"
                        ))
                keyboard.append(row)

            keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="my_expenses")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = """
➕ **Новый расход**

**Шаг 4/5:** Выберите проект

📁 *Выберите проект для привязки расхода или выберите "Без привязки к проекту"*
            """

            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в show_project_selection: {e}")
            await update.message.reply_text("❌ Ошибка при загрузке проектов.")

    async def handle_project_selection(self, query, context):
        """Обработка выбора проекта"""
        try:
            if 'expense_creation' not in context.user_data:
                await query.answer("Сессия создания расхода не найдена.")
                return

            expense_data = context.user_data['expense_creation']

            if query.data == "project_none":
                expense_data['project_id'] = None
                project_name = "Без привязки к проекту"
            else:
                project_id = int(query.data.replace("project_", ""))
                expense_data['project_id'] = project_id

                # Получаем название проекта
                projects = self.get_projects()
                project_name = next((p['name'] for p in projects if p['id'] == project_id), "Неизвестный проект")

            expense_data['step'] = 'description'

            message = f"""
➕ **Новый расход**

**Шаг 5/5:** Добавьте комментарий (необязательно)

📝 **Текущие данные:**
• Наименование: {expense_data['name']}
• Сумма: {expense_data['amount']:,.0f} сум
• Дата: {expense_data['date']}
• Проект: {project_name}

💬 *Введите комментарий к расходу или нажмите кнопку "Пропустить"*
            """

            keyboard = [[InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_description")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Ошибка в handle_project_selection: {e}")
            await query.edit_message_text("❌ Произошла ошибка при выборе проекта.")

    async def handle_skip_description(self, query, context):
        """Пропуск описания и создание расхода"""
        try:
            expense_data = context.user_data['expense_creation']
            expense_data['description'] = ''
            await self.create_expense_from_callback(query, context)

        except Exception as e:
            logger.error(f"Ошибка в handle_skip_description: {e}")
            await query.edit_message_text("❌ Произошла ошибка.")

    async def create_expense(self, update, context):
        """Создание расхода в базе данных"""
        try:
            expense_data = context.user_data['expense_creation']
            user = update.effective_user
            db_user = self.bot.get_user_by_telegram_id(user.id, user.username)

            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден.")
                return

            # Создаем расход в базе данных
            success = self.save_expense_to_db(
                user_id=db_user['id'],
                name=expense_data['name'],
                amount=expense_data['amount'],
                date=expense_data['date'],
                project_id=expense_data['project_id'],
                description=expense_data['description']
            )

            if success:
                # Получаем название проекта для отображения
                project_name = "Без привязки к проекту"
                if expense_data['project_id']:
                    projects = self.get_projects()
                    project_name = next((p['name'] for p in projects if p['id'] == expense_data['project_id']), "Неизвестный проект")

                message = f"""
✅ **Расход успешно добавлен!**

📝 **Детали:**
• Наименование: {expense_data['name']}
• Сумма: {expense_data['amount']:,.0f} сум
• Дата: {expense_data['date']}
• Проект: {project_name}
{f"• Комментарий: {expense_data['description']}" if expense_data['description'] else ""}

💰 Расход сохранен в системе и будет отображаться в отчетах.
                """

                keyboard = [
                    [InlineKeyboardButton("➕ Добавить еще расход", callback_data="add_expense")],
                    [InlineKeyboardButton("📋 Мои расходы", callback_data="view_expenses")],
                    [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    "❌ Не удалось сохранить расход. Попробуйте позже."
                )

            # Очищаем данные создания расхода
            context.user_data.pop('expense_creation', None)

        except Exception as e:
            logger.error(f"Ошибка в create_expense: {e}")
            await update.message.reply_text("❌ Произошла ошибка при создании расхода.")


    def get_projects(self):
        """Получение списка проектов"""
        conn = self.bot.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute("SELECT id, name FROM projects ORDER BY name")
            projects = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return projects
        except Exception as e:
            logger.error(f"Ошибка получения проектов: {e}")
            conn.close()
            return []

    def save_expense_to_db(self, user_id, name, amount, date, project_id=None, description=None):
        """Сохранение расхода в базу данных"""
        conn = self.bot.get_db_connection()
        if not conn:
            return False

        try:
            conn.execute("""
                INSERT INTO employee_expenses (
                    user_id, name, amount, date, project_id, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, name, float(amount), date, project_id, description, datetime.now()
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения расхода: {e}")
            conn.close()
            return False

    def get_user_expenses_by_period(self, user_id, start_date):
        """Получение расходов пользователя за период"""
        conn = self.bot.get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.execute("""
                SELECT
                    ee.id, ee.name, ee.amount, ee.date, ee.description,
                    p.name as project_name
                FROM employee_expenses ee
                LEFT JOIN projects p ON ee.project_id = p.id
                WHERE ee.user_id = ?
                AND ee.created_at >= ?
                ORDER BY ee.created_at DESC
            """, (user_id, start_date))

            expenses = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return expenses
        except Exception as e:
            logger.error(f"Ошибка получения расходов: {e}")
            conn.close()
            return []