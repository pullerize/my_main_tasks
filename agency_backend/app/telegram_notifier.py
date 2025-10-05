"""
Модуль для отправки Telegram уведомлений напрямую через API
"""
import os
import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_task_notification(executor_telegram_id: int, task_id: int, task_data: Dict) -> bool:
    """
    Отправка уведомления исполнителю о новой задаче через Telegram API

    Args:
        executor_telegram_id: Telegram ID исполнителя
        task_id: ID задачи
        task_data: Данные задачи (title, project_name, task_type, deadline_text, format)

    Returns:
        bool: True если уведомление отправлено успешно
    """
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not configured")
        return False

    if not executor_telegram_id:
        logger.warning(f"Executor has no telegram_id, notification not sent for task #{task_id}")
        return False

    try:
        # Формируем текст уведомления
        notification_text = f"""
🔔 **Вам назначена новая задача!**

📋 **Задача #{task_id}**
┌─────────────────────────────────┐
│ 📝 **Название:** {task_data.get('title', 'Без названия')}
│ 📁 **Проект:** {task_data.get('project_name', 'Не указан')}
│ 🏷️ **Тип:** {task_data.get('task_type', 'Не указан')}
"""

        if task_data.get('description'):
            # Ограничиваем длину описания для уведомления
            description = task_data.get('description', '')
            if len(description) > 150:
                description = description[:150] + '...'
            notification_text += f"│ 📄 **Описание:** {description}\n"

        if task_data.get('format'):
            notification_text += f"│ 📐 **Формат:** {task_data.get('format')}\n"

        notification_text += f"│ ⏰ **Дедлайн:** {task_data.get('deadline_text', 'Не установлен')}\n"
        notification_text += "└─────────────────────────────────┘\n\n"
        notification_text += "💡 **Нажмите кнопку ниже, чтобы принять задачу в работу**"

        # Создаем inline кнопку "Принять в работу"
        inline_keyboard = {
            "inline_keyboard": [[
                {
                    "text": "✅ Принять в работу",
                    "callback_data": f"accept_task_{task_id}"
                }
            ]]
        }

        # Отправляем сообщение через Telegram API
        response = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": executor_telegram_id,
                "text": notification_text,
                "parse_mode": "Markdown",
                "reply_markup": inline_keyboard
            },
            timeout=10
        )

        if response.status_code == 200:
            logger.info(f"✅ Уведомление о задаче #{task_id} отправлено пользователю {executor_telegram_id}")
            return True
        else:
            error_data = response.json()
            logger.error(f"❌ Ошибка отправки уведомления: {error_data}")
            return False

    except Exception as e:
        logger.error(f"❌ Исключение при отправке уведомления о задаче #{task_id}: {e}")
        return False
