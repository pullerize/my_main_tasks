#!/bin/bash

# Скрипт для остановки Telegram бота

echo "🛑 Остановка Telegram бота..."

# Останавливаем все запущенные экземпляры
pkill -9 -f "python.*bot\.py" 2>/dev/null

sleep 1

# Проверяем, что все остановлены
if pgrep -f "python.*bot\.py" > /dev/null; then
    echo "❌ Не удалось остановить все экземпляры"
    echo "Запущенные процессы:"
    ps aux | grep "python.*bot\.py" | grep -v grep
    exit 1
else
    echo "✅ Все экземпляры бота остановлены"
fi
