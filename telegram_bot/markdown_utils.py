"""
Утилиты для работы с Markdown в Telegram
"""

def escape_markdown(text):
    """
    Экранирует специальные символы Markdown для безопасного использования в Telegram

    Args:
        text: Текст для экранирования

    Returns:
        Экранированный текст
    """
    if text is None:
        return ""

    text = str(text)

    # Экранируем специальные символы Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, '\\' + char)

    return text


def safe_markdown(text):
    """
    Альтернативный метод: заменяет потенциально опасные символы на безопасные

    Args:
        text: Текст для обработки

    Returns:
        Безопасный текст
    """
    if text is None:
        return ""

    text = str(text)

    # Заменяем опасные символы на похожие безопасные
    replacements = {
        '_': '＿',  # Полноширинное подчеркивание
        '*': '＊',  # Полноширинная звездочка
        '[': '［',  # Полноширинная левая скобка
        ']': '］',  # Полноширинная правая скобка
        '`': '｀',  # Полноширинный обратный апостроф
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text
