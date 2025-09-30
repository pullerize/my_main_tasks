#!/bin/bash

echo "Останавливаем все экземпляры бота..."
pkill -f "python.*bot.py" || true
sleep 2

echo "Запускаем бота..."
python3 bot.py