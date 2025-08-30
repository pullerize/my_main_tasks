#!/bin/bash

# Быстрый запуск Agency Management System для разработки

echo "🚀 Запуск Agency Management System в режиме разработки"

# Останавливаем существующие контейнеры
docker-compose down 2>/dev/null || true

# Создаем директории если не существуют
mkdir -p data/{static,contracts,files}

# Запускаем в режиме разработки
docker-compose up -d --build

echo "⏳ Ждем запуска сервисов..."
sleep 5

# Показываем статус
docker-compose ps

echo ""
echo "🌐 Сервисы доступны:"
echo "  Frontend:  http://localhost"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "📋 Полезные команды:"
echo "  Логи:      docker-compose logs -f"
echo "  Остановка: docker-compose down"
echo "  Рестарт:   docker-compose restart"