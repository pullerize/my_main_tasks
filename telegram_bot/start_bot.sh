#!/bin/bash

echo "Останавливаем все экземпляры бота..."
pkill -f "python.*bot.py" || true
sleep 2

echo "Запускаем бота..."
nohup python3 bot.py > telegram_bot.log 2>&1 &

sleep 2

# Проверяем, что бот запустился
if pgrep -f "python.*bot\.py" > /dev/null; then
    echo "✅ Бот успешно запущен (PID: $(pgrep -f 'python.*bot\.py'))"
    echo "📄 Логи: tail -f telegram_bot.log"
else
    echo "❌ Ошибка запуска бота"
    exit 1
fi