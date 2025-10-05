#!/bin/bash

# 🚀 8Bit Codex - Автоматический скрипт развертывания
# Использование: ./deploy.sh

set -e  # Остановка при ошибках

echo "=========================================="
echo "🚀 8Bit Codex Production Deployment"
echo "Домен: 8bit-task.site"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для красивого вывода
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия .env файла
if [ ! -f .env ]; then
    error ".env файл не найден!"
    info "Создайте .env файл на основе .env.example:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

info "✓ .env файл найден"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    error "Docker не установлен!"
    echo "Установите Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

info "✓ Docker установлен"

# Проверка Docker Compose
if ! docker compose version &> /dev/null; then
    error "Docker Compose не установлен!"
    exit 1
fi

info "✓ Docker Compose установлен"

# Создание необходимых директорий
info "Создание директорий..."
mkdir -p certbot-www
mkdir -p agency_backend/uploads/leads
mkdir -p agency_backend/files
mkdir -p agency_backend/contracts
mkdir -p agency_backend/static/projects
mkdir -p agency_backend/static/digital

info "✓ Директории созданы"

# Проверка обязательных переменных в .env
info "Проверка конфигурации..."

check_env_var() {
    local var_name=$1
    local default_value=$2
    
    if grep -q "^${var_name}=${default_value}" .env; then
        warn "${var_name} использует дефолтное значение! Измените в .env"
        return 1
    fi
    return 0
}

# Проверка критичных переменных
WARNINGS=0

if ! check_env_var "SECRET_KEY" "CHANGE_THIS_TO_SECURE_RANDOM_STRING_32_CHARS"; then
    ((WARNINGS++))
fi

if ! check_env_var "POSTGRES_PASSWORD" "CHANGE_THIS_TO_SECURE_PASSWORD"; then
    ((WARNINGS++))
fi

if ! check_env_var "BOT_TOKEN" "your-telegram-bot-token-here"; then
    ((WARNINGS++))
fi

if [ $WARNINGS -gt 0 ]; then
    echo ""
    error "Найдено $WARNINGS предупреждений в .env!"
    echo ""
    read -p "Продолжить развертывание? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

info "✓ Конфигурация проверена"

# Выбор режима развертывания
echo ""
echo "Выберите действие:"
echo "  1) Первичное развертывание (с получением SSL)"
echo "  2) Обновление приложения"
echo "  3) Перезапуск сервисов"
echo "  4) Просмотр логов"
echo "  5) Остановка всех сервисов"
echo ""
read -p "Введите номер (1-5): " -n 1 -r
echo ""

case $REPLY in
    1)
        info "=== ПЕРВИЧНОЕ РАЗВЕРТЫВАНИЕ ==="
        
        # Сборка образов
        info "Сборка Docker образов..."
        docker compose -f docker-compose.production.yml build
        
        # Запуск БД
        info "Запуск базы данных..."
        docker compose -f docker-compose.production.yml up -d db
        sleep 10
        
        # Запуск backend и frontend
        info "Запуск backend и frontend..."
        docker compose -f docker-compose.production.yml up -d backend frontend
        sleep 5
        
        # Запуск Nginx без SSL
        info "Запуск Nginx для получения SSL..."
        docker compose -f docker-compose.production.yml up -d nginx
        
        # Получение SSL сертификата
        info "Получение SSL сертификата..."
        warn "Введите email для Let's Encrypt:"
        read -p "Email: " LETSENCRYPT_EMAIL
        
        docker compose -f docker-compose.production.yml run --rm certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email "$LETSENCRYPT_EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d 8bit-task.site \
            -d www.8bit-task.site
        
        # Перезапуск Nginx с SSL
        info "Перезапуск Nginx с SSL..."
        docker compose -f docker-compose.production.yml restart nginx
        
        # Запуск Telegram бота
        info "Запуск Telegram бота..."
        docker compose -f docker-compose.production.yml up -d telegram_bot
        
        # Запуск Certbot для автообновления
        docker compose -f docker-compose.production.yml up -d certbot
        
        info "✓ Развертывание завершено!"
        ;;
        
    2)
        info "=== ОБНОВЛЕНИЕ ПРИЛОЖЕНИЯ ==="
        
        info "Получение последних изменений..."
        git pull origin main || warn "Git pull не выполнен"
        
        info "Пересборка и перезапуск..."
        docker compose -f docker-compose.production.yml up -d --build
        
        info "Удаление неиспользуемых образов..."
        docker image prune -f
        
        info "✓ Обновление завершено!"
        ;;
        
    3)
        info "=== ПЕРЕЗАПУСК СЕРВИСОВ ==="
        docker compose -f docker-compose.production.yml restart
        info "✓ Сервисы перезапущены!"
        ;;
        
    4)
        info "=== ПРОСМОТР ЛОГОВ ==="
        echo "Для выхода нажмите Ctrl+C"
        docker compose -f docker-compose.production.yml logs -f
        ;;
        
    5)
        info "=== ОСТАНОВКА СЕРВИСОВ ==="
        docker compose -f docker-compose.production.yml down
        info "✓ Все сервисы остановлены!"
        ;;
        
    *)
        error "Неверный выбор!"
        exit 1
        ;;
esac

echo ""
info "=========================================="
info "Статус сервисов:"
docker compose -f docker-compose.production.yml ps
echo ""
info "Полезные команды:"
echo "  • Логи:          docker compose logs -f [сервис]"
echo "  • Статус:        docker compose ps"
echo "  • Перезапуск:    docker compose restart [сервис]"
echo "  • Остановка:     docker compose down"
echo ""
info "Сайт доступен: https://8bit-task.site"
info "API документация: https://8bit-task.site/docs"
info "=========================================="
