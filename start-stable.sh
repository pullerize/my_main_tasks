#!/bin/bash

# 8bit-codex - Стабильный запуск серверов
# Использование: ./start-stable.sh

echo "🚀 8bit-codex - Стабильный запуск..."

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Создание директории для логов
mkdir -p logs

# Функция остановки
cleanup() {
    echo -e "\n${YELLOW}🛑 Остановка серверов...${NC}"
    pkill -f "uvicorn agency_backend.app.main:app"
    pkill -f "vite.*--port"
    exit 0
}
trap cleanup INT TERM

# Активация venv
source venv/bin/activate

echo -e "${GREEN}✅ Запуск backend (стабильный режим)...${NC}"

# Запуск backend без reload для стабильности
uvicorn agency_backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 > logs/backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

echo -e "${GREEN}✅ Запуск frontend...${NC}"

# Запуск frontend
cd agency_frontend
npx vite --port 5173 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 2

# Проверка что серверы запустились
if kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${GREEN}🎉 Серверы запущены успешно!${NC}"
    echo -e "${GREEN}📱 Frontend: http://localhost:5173${NC}"
    echo -e "${GREEN}🔧 Backend: http://localhost:8000${NC}"
    echo -e "${BLUE}📋 Логи: logs/backend.log, logs/frontend.log${NC}"
else
    echo -e "${RED}❌ Ошибка запуска серверов${NC}"
    exit 1
fi

# Мониторинг и автоперезагрузка
echo -e "${YELLOW}🔄 Запущен мониторинг серверов (автоперезагрузка)${NC}"
echo -e "${YELLOW}💡 Ctrl+C для остановки${NC}"

while true; do
    sleep 10
    
    # Проверка backend
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Backend упал, перезапуск...${NC}"
        uvicorn agency_backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 >> logs/backend.log 2>&1 &
        BACKEND_PID=$!
        sleep 3
    fi
    
    # Проверка frontend
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Frontend упал, перезапуск...${NC}"
        cd agency_frontend
        npx vite --port 5173 --host 0.0.0.0 >> ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
        sleep 3
    fi
    
    # Проверка HTTP ответов
    if ! curl -s --max-time 5 http://localhost:8000 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Backend не отвечает, перезапуск...${NC}"
        kill $BACKEND_PID 2>/dev/null
        sleep 2
        uvicorn agency_backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 >> logs/backend.log 2>&1 &
        BACKEND_PID=$!
        sleep 3
    fi
    
    if ! curl -s --max-time 5 http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Frontend не отвечает, перезапуск...${NC}"
        kill $FRONTEND_PID 2>/dev/null
        sleep 2
        cd agency_frontend
        npx vite --port 5173 --host 0.0.0.0 >> ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        cd ..
        sleep 3
    fi
done