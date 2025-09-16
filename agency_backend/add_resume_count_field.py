#!/usr/bin/env python3

"""
Миграция для добавления поля resume_count в таблицу tasks
"""

import sqlite3
import os
from datetime import datetime

# Путь к базе данных
DB_PATH = "shared_database.db"

def migrate_add_resume_count():
    """Добавляет поле resume_count в таблицу tasks"""

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        return False

    print(f"🔄 Начинаем миграцию базы данных {DB_PATH}...")

    # Создаем резервную копию
    backup_path = f"{DB_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Создана резервная копия: {backup_path}")
    except Exception as e:
        print(f"⚠️  Не удалось создать резервную копию: {e}")
        print("Продолжаем без резервной копии...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Проверяем, есть ли уже поле resume_count
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'resume_count' in columns:
            print("✅ Поле resume_count уже существует в таблице tasks")
            return True

        print("📝 Добавляем поле resume_count в таблицу tasks...")

        # Добавляем новое поле
        cursor.execute("ALTER TABLE tasks ADD COLUMN resume_count INTEGER DEFAULT 0")

        # Устанавливаем значение по умолчанию для существующих записей
        cursor.execute("UPDATE tasks SET resume_count = 0 WHERE resume_count IS NULL")

        # Сохраняем изменения
        conn.commit()

        print("✅ Поле resume_count успешно добавлено!")

        # Проверяем результат
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()
        print("\n📋 Текущая структура таблицы tasks:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Запуск миграции для добавления поля resume_count")

    if migrate_add_resume_count():
        print("\n🎉 Миграция завершена успешно!")
        print("\nТеперь можно запустить сервер:")
        print("cd agency_backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n💥 Миграция завершилась с ошибкой!")
        print("Проверьте логи выше для получения подробной информации.")