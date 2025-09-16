#!/usr/bin/env python3

"""
Исправление таблицы lead_notes - добавление поля lead_status
"""

import sqlite3
import os
from datetime import datetime

# Путь к базе данных
DB_PATH = "shared_database.db"

def fix_lead_notes_table():
    """Добавляет поле lead_status в таблицу lead_notes"""

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        return False

    print(f"🔄 Исправляем таблицу lead_notes в базе данных {DB_PATH}...")

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
        # Проверяем, есть ли уже поле lead_status
        cursor.execute("PRAGMA table_info(lead_notes)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'lead_status' in columns:
            print("✅ Поле lead_status уже существует в таблице lead_notes")
            return True

        print("📝 Добавляем поле lead_status в таблицу lead_notes...")

        # Добавляем новое поле
        cursor.execute("ALTER TABLE lead_notes ADD COLUMN lead_status VARCHAR")

        # Сохраняем изменения
        conn.commit()

        print("✅ Поле lead_status успешно добавлено!")

        # Проверяем результат
        cursor.execute("PRAGMA table_info(lead_notes)")
        columns = cursor.fetchall()
        print("\n📋 Текущая структура таблицы lead_notes:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка при выполнении исправления: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Запуск исправления таблицы lead_notes")

    if fix_lead_notes_table():
        print("\n🎉 Исправление завершено успешно!")
        print("\nТеперь можно перезапустить сервер:")
        print("cd agency_backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n💥 Исправление завершилось с ошибкой!")
        print("Проверьте логи выше для получения подробной информации.")