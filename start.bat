@echo off
title 8bit-codex Server
echo 🚀 8bit-codex - Запуск стабильных серверов...

REM Переход в директорию проекта
cd /d "%~dp0"

REM Запуск через WSL для максимальной стабильности
wsl bash -c "cd '/mnt/c/Users/Господин/Desktop/Мои проекты/8bit_tasks/8bit-codex' && ./start-stable.sh"

pause