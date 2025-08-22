#!/bin/bash

# 8bit-codex Production Deployment Script
# Использование: ./deploy.sh

echo "🚀 8bit-codex - Production Deployment"
echo "======================================"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Получение публичного IP
echo -e "${BLUE}📡 Определение вашего IP адреса...${NC}"
PUBLIC_IP=$(curl -s ifconfig.me)
echo -e "${GREEN}✅ Ваш публичный IP: $PUBLIC_IP${NC}"

# Запрос подтверждения
echo ""
echo -e "${YELLOW}⚠️  ВАЖНО: Перед продолжением убедитесь, что:${NC}"
echo "1. У вас есть статический IP адрес или настроен DDNS"
echo "2. На роутере настроена переадресация портов:"
echo "   - Порт 3000 → Ваш компьютер:3000 (Frontend)"
echo "   - Порт 8000 → Ваш компьютер:8000 (Backend)"
echo "3. Docker и docker-compose установлены"
echo ""
read -p "Продолжить? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ Деплой отменен${NC}"
    exit 1
fi

# Обновление конфигураций с реальным IP
echo -e "${BLUE}🔧 Обновление конфигураций...${NC}"

# Обновление frontend .env.production
sed -i "s/YOUR_PUBLIC_IP/$PUBLIC_IP/g" agency_frontend/.env.production

# Обновление backend .env.production
sed -i "s/YOUR_PUBLIC_IP/$PUBLIC_IP/g" .env.production

# Генерация SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
sed -i "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/g" .env.production

echo -e "${GREEN}✅ Конфигурации обновлены${NC}"

# Остановка старых контейнеров
echo -e "${BLUE}🛑 Остановка старых контейнеров...${NC}"
docker-compose -f docker-compose.production.yml down

# Сборка и запуск
echo -e "${BLUE}🏗️  Сборка Docker образов...${NC}"
docker-compose -f docker-compose.production.yml build

echo -e "${BLUE}🚀 Запуск приложения...${NC}"
docker-compose -f docker-compose.production.yml up -d

# Проверка статуса
echo -e "${BLUE}🔍 Проверка статуса...${NC}"
sleep 5

if docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ Приложение успешно запущено!${NC}"
    echo ""
    echo -e "${GREEN}🌐 Доступ к приложению:${NC}"
    echo -e "   Frontend: ${BLUE}http://$PUBLIC_IP:3000${NC}"
    echo -e "   Backend API: ${BLUE}http://$PUBLIC_IP:8000${NC}"
    echo ""
    echo -e "${YELLOW}📝 Логи:${NC}"
    echo "   docker-compose -f docker-compose.production.yml logs -f"
    echo ""
    echo -e "${YELLOW}🛑 Остановка:${NC}"
    echo "   docker-compose -f docker-compose.production.yml down"
else
    echo -e "${RED}❌ Ошибка запуска. Проверьте логи:${NC}"
    echo "   docker-compose -f docker-compose.production.yml logs"
    exit 1
fi