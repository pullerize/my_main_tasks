#!/usr/bin/env python3
"""
Скрипт для очистки webhook и остановки всех экземпляров бота
"""

import asyncio
import os
import sys
import subprocess
import platform
from telegram import Bot

BOT_TOKEN = "8406944062:AAGcoChWxQV-JMtjt_9aX3Fnm8R-vrWNQpQ"

async def clear_webhook():
    """Очистить webhook"""
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook очищен, обновления сброшены")

        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот: @{me.username}")

        return True
    except Exception as e:
        print(f"❌ Ошибка при очистке webhook: {e}")
        return False

def kill_all_bots():
    """Убить все процессы бота"""
    killed = False

    # Для Windows
    if platform.system() == 'Windows':
        try:
            # Убиваем все процессы Python с bot.py
            result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'],
                                  capture_output=True, text=True)
            if "SUCCESS" in result.stdout:
                print("✅ Процессы бота остановлены (Windows)")
                killed = True
        except:
            pass

    # Для Linux/Unix
    try:
        result = subprocess.run(['pkill', '-f', 'bot.py'],
                              capture_output=True)
        if result.returncode == 0:
            print("✅ Процессы бота остановлены (Linux)")
            killed = True
    except:
        pass

    # Удаляем lock-файлы
    lock_files = [
        '/tmp/telegram_bot.lock',
        os.path.join(os.environ.get('TEMP', ''), 'telegram_bot.lock'),
        '/c/Users/Господин/AppData/Local/Temp/telegram_bot.lock'
    ]

    for lock_file in lock_files:
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
                print(f"✅ Удален lock-файл: {lock_file}")
        except:
            pass

    if not killed:
        print("ℹ️ Процессы бота не найдены")

    return True

async def main():
    print("🧹 Очистка бота...")
    print("-" * 40)

    # Убиваем все процессы
    kill_all_bots()

    # Ждем немного
    await asyncio.sleep(1)

    # Очищаем webhook
    await clear_webhook()

    print("-" * 40)
    print("✅ Готово! Теперь можно запускать бота:")
    print("   python bot.py")
    print("   или")
    print("   python bot.py --force")

if __name__ == "__main__":
    asyncio.run(main())