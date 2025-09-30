#!/usr/bin/env python3

"""
Система обработки ошибок - централизованная обработка всех ошибок бота
"""

import traceback
from typing import Union, Optional
from telegram import Update
from telegram.ext import CallbackContext
from config import logger


class ErrorHandler:
    """Централизованная система обработки ошибок"""

    @staticmethod
    async def handle_error(update: Update, context: CallbackContext):
        """Глобальный обработчик ошибок для telegram bot"""
        error = context.error
        logger.error(f"Telegram bot error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Попытаемся отправить пользователю сообщение об ошибке
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="😔 Произошла ошибка при обработке запроса. Попробуйте позже."
                )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

    @staticmethod
    async def safe_edit_message(query_or_update: Union[Update, object], text: str, **kwargs) -> bool:
        """Безопасное редактирование сообщения с обработкой разных типов объектов"""
        try:
            # Определяем тип объекта и получаем query
            if hasattr(query_or_update, 'callback_query') and query_or_update.callback_query:
                query = query_or_update.callback_query
                await query.edit_message_text(text, **kwargs)
                return True
            elif hasattr(query_or_update, 'edit_message_text'):
                # Это уже CallbackQuery
                await query_or_update.edit_message_text(text, **kwargs)
                return True
            else:
                logger.warning(f"Неподдерживаемый тип объекта для edit_message_text: {type(query_or_update)}")
                return False

        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            return False

    @staticmethod
    async def safe_reply(update: Update, text: str, **kwargs) -> bool:
        """Безопасная отправка ответа пользователю"""
        try:
            if update.message:
                await update.message.reply_text(text, **kwargs)
                return True
            elif update.callback_query:
                await update.callback_query.message.reply_text(text, **kwargs)
                return True
            else:
                logger.warning("Не удалось определить способ отправки ответа")
                return False

        except Exception as e:
            logger.error(f"Ошибка отправки ответа: {e}")
            return False

    @staticmethod
    def log_function_call(func_name: str, user_id: Optional[int] = None, extra_info: str = ""):
        """Логирование вызовов функций для отладки"""
        user_info = f" (user: {user_id})" if user_id else ""
        extra = f" - {extra_info}" if extra_info else ""
        logger.info(f"📞 {func_name}{user_info}{extra}")

    @staticmethod
    def handle_api_error(error: Exception, operation: str) -> str:
        """Обработка ошибок API с возвратом пользовательского сообщения"""
        logger.error(f"API error during {operation}: {error}")

        error_str = str(error).lower()

        if "connection" in error_str or "timeout" in error_str:
            return "🔌 Проблемы с подключением к серверу. Попробуйте позже."
        elif "403" in error_str or "forbidden" in error_str:
            return "🚫 Недостаточно прав для выполнения операции."
        elif "404" in error_str or "not found" in error_str:
            return "🔍 Запрашиваемые данные не найдены."
        elif "500" in error_str or "internal server error" in error_str:
            return "⚙️ Внутренняя ошибка сервера. Обратитесь к администратору."
        else:
            return "😔 Произошла ошибка при обработке запроса. Попробуйте позже."

    @staticmethod
    def handle_database_error(error: Exception, operation: str) -> str:
        """Обработка ошибок базы данных"""
        logger.error(f"Database error during {operation}: {error}")

        error_str = str(error).lower()

        if "locked" in error_str:
            return "🔒 База данных временно заблокирована. Попробуйте через несколько секунд."
        elif "constraint" in error_str or "unique" in error_str:
            return "📝 Данные уже существуют или нарушают ограничения."
        elif "no such table" in error_str or "no such column" in error_str:
            return "🗃️ Ошибка структуры базы данных. Обратитесь к администратору."
        else:
            return "💾 Ошибка при работе с базой данных. Попробуйте позже."


# Декораторы для обработки ошибок
def handle_errors(operation_name: str = ""):
    """Декоратор для автоматической обработки ошибок в функциях бота"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Попытаемся найти update объект в аргументах
                update = None
                for arg in args:
                    if isinstance(arg, Update):
                        update = arg
                        break

                if update:
                    error_message = ErrorHandler.handle_api_error(e, operation_name or func.__name__)
                    await ErrorHandler.safe_reply(update, error_message)

        return wrapper
    return decorator


def safe_database_operation(operation_name: str = ""):
    """Декоратор для безопасных операций с базой данных"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_message = ErrorHandler.handle_database_error(e, operation_name or func.__name__)
                logger.error(f"Database operation failed: {error_message}")
                raise Exception(error_message)

        return wrapper
    return decorator