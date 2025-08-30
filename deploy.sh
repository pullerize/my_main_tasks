#!/bin/bash

# Скрипт развертывания Agency Management System
# Используйте: ./deploy.sh [development|production]

set -e

ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Развертывание Agency Management System (окружение: $ENVIRONMENT)"

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

# Переходим в директорию проекта
cd "$SCRIPT_DIR"

# Проверяем наличие необходимых файлов
if [[ ! -f ".env" && -f ".env.example" ]]; then
    echo "📝 Создаем .env файл из .env.example"
    cp .env.example .env
    echo "⚠️  ВНИМАНИЕ: Отредактируйте .env файл перед запуском в продакшене!"
fi

# Создаем директорию для данных
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "📁 Создаем директории для продакшена"
    sudo mkdir -p /data/agency/{static,contracts,files}
    sudo chown -R $USER:$USER /data/agency
    
    # Останавливаем существующие контейнеры
    echo "🛑 Останавливаем существующие контейнеры"
    docker-compose -f docker-compose.production.yml down || true
    
    # Собираем и запускаем продакшен
    echo "🔨 Собираем Docker образы"
    docker-compose -f docker-compose.production.yml build --no-cache
    
    echo "🚀 Запускаем в продакшене"
    docker-compose -f docker-compose.production.yml up -d
else
    # Development окружение
    mkdir -p data/{static,contracts,files}
    
    # Останавливаем существующие контейнеры
    echo "🛑 Останавливаем существующие контейнеры"
    docker-compose down || true
    
    # Собираем и запускаем development
    echo "🔨 Собираем Docker образы"
    docker-compose build --no-cache
    
    echo "🚀 Запускаем в режиме разработки"
    docker-compose up -d
fi

# Ждем запуска сервисов
echo "⏳ Ждем запуска сервисов..."
sleep 10

# Проверяем состояние контейнеров
echo "📊 Состояние контейнеров:"
if [[ "$ENVIRONMENT" == "production" ]]; then
    docker-compose -f docker-compose.production.yml ps
else
    docker-compose ps
fi

# Проверяем доступность сервисов
echo "🔍 Проверяем доступность сервисов..."

# Проверяем backend
if curl -f http://localhost:8000/ &>/dev/null; then
    echo "✅ Backend доступен на http://localhost:8000"
else
    echo "❌ Backend недоступен"
fi

# Проверяем frontend
if curl -f http://localhost/ &>/dev/null; then
    echo "✅ Frontend доступен на http://localhost"
else
    echo "❌ Frontend недоступен"
fi

echo ""
echo "🎉 Развертывание завершено!"
echo ""
echo "📚 Полезные команды:"
echo "  Просмотр логов:     docker-compose logs -f"
echo "  Остановка:          docker-compose down"
echo "  Перезапуск:         docker-compose restart"
echo ""

if [[ "$ENVIRONMENT" == "development" ]]; then
    echo "🌐 Доступ к приложению:"
    echo "  Frontend:  http://localhost"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
else
    echo "🌐 Приложение запущено в продакшене"
    echo "⚠️  Не забудьте настроить SSL-сертификаты и домен!"
fi