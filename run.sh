#!/bin/bash

# 8bit-codex - Запуск одной командой
# Использование: ./run.sh

echo "🚀 8bit-codex - Запуск приложения..."

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Проверка зависимостей
echo -e "${BLUE}🔍 Проверка зависимостей...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js не найден${NC}"
    exit 1
fi

# Создание venv если нет
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Создание venv...${NC}"
    python3 -m venv venv
fi

# Активация venv
source venv/bin/activate

# Установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
pip install -q -r agency_backend/requirements.txt
cd agency_frontend && npm install --silent && cd ..

# Функция остановки
cleanup() {
    echo -e "\n${YELLOW}🛑 Остановка...${NC}"
    kill $BACKEND_PID 2>/dev/null
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

echo -e "${GREEN}✅ Запуск сервисов...${NC}"

# Запуск backend
uvicorn agency_backend.app.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!
sleep 2

# Запуск frontend
cd agency_frontend
[ -f "vite.config.ts" ] && mv vite.config.ts vite.config.ts.backup
npx vite --port 5173 --host &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}🎉 Готово!${NC}"
echo -e "${GREEN}📱 Frontend: http://localhost:5173${NC}"
echo -e "${GREEN}🔧 Backend: http://localhost:8000${NC}"

# Открытие браузера
sleep 3
if command -v powershell.exe &> /dev/null; then
    powershell.exe -c "Start-Process 'http://localhost:5173'" 2>/dev/null
fi

echo -e "${YELLOW}💡 Ctrl+C для остановки${NC}"
wait $BACKEND_PID