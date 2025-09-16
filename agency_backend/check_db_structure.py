#!/usr/bin/env python3

"""
Проверка структуры базы данных и добавление недостающих полей
"""

import sqlite3
import os

DB_PATH = "shared_database.db"

def check_and_fix_db_structure():
    """Проверяет и исправляет структуру базы данных"""

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных {DB_PATH} не найдена!")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Получаем текущую структуру таблицы tasks
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {column[1]: column[2] for column in cursor.fetchall()}

        print("📋 Текущая структура таблицы tasks:")
        for name, type_name in columns.items():
            print(f"  - {name} ({type_name})")

        # Проверяем и добавляем недостающие поля
        missing_fields = []

        if 'accepted_at' not in columns:
            missing_fields.append(('accepted_at', 'DATETIME'))

        if 'resume_count' not in columns:
            missing_fields.append(('resume_count', 'INTEGER DEFAULT 0'))

        if 'is_recurring' not in columns:
            missing_fields.append(('is_recurring', 'BOOLEAN'))

        if 'recurrence_type' not in columns:
            missing_fields.append(('recurrence_type', 'VARCHAR'))

        if 'recurrence_time' not in columns:
            missing_fields.append(('recurrence_time', 'VARCHAR'))

        if 'recurrence_days' not in columns:
            missing_fields.append(('recurrence_days', 'VARCHAR'))

        if 'next_run_at' not in columns:
            missing_fields.append(('next_run_at', 'DATETIME'))

        if missing_fields:
            print(f"\n🔧 Добавляем недостающие поля: {[field[0] for field in missing_fields]}")

            for field_name, field_type in missing_fields:
                try:
                    cursor.execute(f"ALTER TABLE tasks ADD COLUMN {field_name} {field_type}")
                    print(f"  ✅ Добавлено поле: {field_name}")
                except Exception as e:
                    print(f"  ❌ Ошибка при добавлении {field_name}: {e}")

            # Устанавливаем значения по умолчанию
            if 'resume_count' in [field[0] for field in missing_fields]:
                cursor.execute("UPDATE tasks SET resume_count = 0 WHERE resume_count IS NULL")

            conn.commit()
            print("✅ Все недостающие поля добавлены!")
        else:
            print("✅ Все необходимые поля присутствуют!")

        # Проверяем финальную структуру
        cursor.execute("PRAGMA table_info(tasks)")
        final_columns = cursor.fetchall()
        print("\n📋 Финальная структура таблицы tasks:")
        for col in final_columns:
            print(f"  - {col[1]} ({col[2]})")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    print("🔍 Проверка структуры базы данных...")
    check_and_fix_db_structure()